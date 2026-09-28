"""
app/main.py
Main API application entry point.
"""
import asyncio
import io
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pdf2image import convert_from_bytes
from PIL import Image

# Import Config
from app.config import config
from app.security import require_access
from app.reports import issue_report, read_report

# Import Schemas
from app.schemas import (
    CertificateAnalysisResponse,
    ExtractionResult,
    ManualVerificationRequest,
    ForensicsResult
)

# Import Agents
from app.agents.forensics.forensics import ForensicsAgent
from app.agents.ext import ExtractionAgent
from app.agents.verification.service import get_verification_service
from app.agents.verification.scanner import close_browser

# Initialize Logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=config.LOG_LEVEL)

MAX_IMAGE_PIXELS = 50_000_000  # decompression-bomb guard

@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await close_browser()


app = FastAPI(title="Multi-Agent Certificate Verifier", lifespan=lifespan)

# CORS Setup (origins come from ALLOWED_ORIGINS; no wildcard together with credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Initialize Agents
forensics_agent = ForensicsAgent(use_trufor=True)

if config.MISTRAL_API_KEY:
    extraction_agent: Optional[ExtractionAgent] = ExtractionAgent(api_key=config.MISTRAL_API_KEY)
else:
    extraction_agent = None
    logger.error("MISTRAL_API_KEY is not set: /verify will return 503 until it is configured.")

verification_service = get_verification_service()

# Bound the number of heavy pipelines (OCR + TruFor + Chromium) running at once
_verify_slots = asyncio.Semaphore(config.MAX_CONCURRENT_VERIFICATIONS)


def _detect_kind(data: bytes) -> Optional[str]:
    """Identify the upload from its magic bytes (the client Content-Type is not trusted)."""
    if data.startswith(b"%PDF-"):
        return "pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image"
    if data.startswith(b"\xff\xd8\xff"):
        return "image"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image"
    return None


async def _read_limited(file: UploadFile) -> bytes:
    """Read the upload, aborting as soon as it exceeds MAX_UPLOAD_BYTES."""
    chunks, size = [], 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > config.MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum is {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _pdf_first_page_to_png(pdf_bytes: bytes) -> bytes:
    """Blocking: render only page 1 of the PDF."""
    images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1, dpi=200)
    if not images:
        raise ValueError("PDF is empty or unreadable.")
    buf = io.BytesIO()
    images[0].save(buf, format="PNG")
    return buf.getvalue()


def _validate_image(image_bytes: bytes) -> None:
    """Blocking: make sure the bytes decode as an image of sane dimensions."""
    with Image.open(io.BytesIO(image_bytes)) as img:
        if img.width * img.height > MAX_IMAGE_PIXELS:
            raise ValueError("Image dimensions are too large.")
        img.verify()


def _to_forensics_result(data: dict) -> ForensicsResult:
    """The forensics agent returns a rich dict; keep only the fields the API exposes."""
    return ForensicsResult(**{k: v for k, v in data.items() if k in ForensicsResult.model_fields})


@app.get("/health")
async def health():
    return {"status": "ok", "extraction_configured": extraction_agent is not None}


@app.get("/report")
async def get_report(token: str = Query(..., max_length=4096)):
    """Validate a signed report token; only reports issued by this server are returned."""
    payload = read_report(token)
    if payload is None:
        raise HTTPException(status_code=404, detail="Report not found or invalid.")
    return {"valid": True, **payload}


@app.post("/verify", response_model=CertificateAnalysisResponse, dependencies=[Depends(require_access)])
async def verify_certificate(file: UploadFile = File(...)):
    """
    Orchestrates the workflow:
    1. Forensics (ELA/Photoshop Detection)
    2. Extraction (OCR)
    3. Verification (URL & Domain Check via Playwright/Httpx)
    """
    if extraction_agent is None:
        raise HTTPException(status_code=503, detail="Service is not configured.")

    # 1. File Pre-processing
    file_bytes = await _read_limited(file)
    kind = _detect_kind(file_bytes)

    if kind == "pdf":
        try:
            image_bytes = await run_in_threadpool(_pdf_first_page_to_png, file_bytes)
        except Exception as e:
            logger.warning(f"PDF processing failed: {e}")
            raise HTTPException(status_code=400, detail="Failed to process PDF. The file may be corrupt or encrypted.")
    elif kind == "image":
        image_bytes = file_bytes
    else:
        raise HTTPException(status_code=400, detail="File must be a JPEG, PNG or WebP image, or a PDF.")

    try:
        await run_in_threadpool(_validate_image, image_bytes)
    except Exception as e:
        logger.warning(f"Image validation failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid or unsupported image.")

    try:
        await asyncio.wait_for(_verify_slots.acquire(), timeout=config.QUEUE_WAIT_SECONDS)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="Server is busy. Please retry shortly.")

    try:
        # --- STAGE 1: FORENSICS ---
        forensics_raw = await run_in_threadpool(forensics_agent.analyze, image_bytes)
        forensics_data = _to_forensics_result(forensics_raw)

        # --- STAGE 2: EXTRACTION ---
        extraction_data = await extraction_agent.extract(image_bytes)
        extraction_result = ExtractionResult(**extraction_data)

        # --- STAGE 3: VERIFICATION ---
        verification_result = await verification_service.verify(extraction_result)

        # --- STAGE 4: FINAL VERDICT (fails closed) ---
        if forensics_data.is_high_risk:
            final_verdict = "FLAGGED (High Risk)"
        elif forensics_data.inconclusive:
            # Forensics could not run to completion: never upgrade to VERIFIED
            final_verdict = "UNVERIFIED"
        elif verification_result.is_verified:
            final_verdict = "VERIFIED"
        else:
            final_verdict = "UNVERIFIED"

        report_token = None
        if final_verdict == "VERIFIED":
            report_token = issue_report({
                "scope": "document",
                "verdict": final_verdict,
                "candidate_name": extraction_result.candidate_name,
                "certificate_id": extraction_result.certificate_id,
                "issuer_name": (extraction_result.issuer_name.value if extraction_result.issuer_name else extraction_result.issuer_org),
                "verification_url": verification_result.verification_url,
                "method": verification_result.method,
                "forensics_status": forensics_data.status,
            })

        return CertificateAnalysisResponse(
            filename=file.filename or "upload",
            final_verdict=final_verdict,
            forensics=forensics_data,
            extraction=extraction_result,
            verification=verification_result,
            report_token=report_token
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation Error: {e}")
        raise HTTPException(status_code=400, detail="Invalid data format.")
    except TimeoutError as e:
        logger.error(f"Timeout Error: {e}")
        raise HTTPException(status_code=504, detail="Processing timed out.")
    except Exception as e:
        logger.error(f"System Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error.")
    finally:
        _verify_slots.release()


@app.post("/verify/manual", response_model=CertificateAnalysisResponse, dependencies=[Depends(require_access)])
async def manual_verification(request: ManualVerificationRequest):
    """
    Handle manual verification with User provided ID and URL.
    The URL must belong to a trusted issuer domain; forensics are not run, so the
    result only says whether the issuer page contains this certificate ID.
    """
    try:
        logger.info(f"Received manual verification request for ID: {request.certificate_id}")

        verification_result = await verification_service.manual_verify(
            request.certificate_id,
            request.issuer_url
        )

        return CertificateAnalysisResponse(
            filename="Manual Verification",
            final_verdict="VERIFIED" if verification_result.is_verified else "UNVERIFIED",
            forensics=ForensicsResult(
                manipulation_score=0.0,
                is_high_risk=False,
                status="skipped",
                details=["Manual verification skipped forensics"]
            ),
            extraction=ExtractionResult(
                candidate_name="Unknown (Manual)",
                certificate_id=request.certificate_id,
                issuer_url=request.issuer_url
            ),
            verification=verification_result,
            report_token=(
                issue_report({
                    "scope": "id_only",   # only the ID was found on the issuer page; holder not checked
                    "verdict": "VERIFIED",
                    "candidate_name": None,
                    "certificate_id": request.certificate_id,
                    "issuer_name": None,
                    "verification_url": verification_result.verification_url,
                    "method": verification_result.method,
                    "forensics_status": "skipped",
                }) if verification_result.is_verified else None
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Manual Verification Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Manual verification failed.")
