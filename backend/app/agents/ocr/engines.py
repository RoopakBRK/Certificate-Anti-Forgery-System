"""
app/agents/ocr/engines.py
Independent OCR engines. Each one turns a prepared RGB page image into text; the
ensemble runs them in parallel and votes on the fields they agree on.

  tesseract  - fast classical OCR, two passes (full page + binarised sparse text)
  paddle     - PaddleOCR 3 (PP-OCRv5 mobile det + English rec), best on stylised certificates
  easyocr    - CRAFT + CRNN, strong on faint / light-grey text
  mistral    - Mistral OCR cloud model (opt-in: sends the image to Mistral)
  pdf_text   - the PDF's embedded text layer (only for digital PDFs)
"""
import base64
import io
import logging
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageOps

from app.config import config

logger = logging.getLogger(__name__)

# PaddleX otherwise probes model hosters on import, which stalls offline servers
os.environ.setdefault("DISABLE_MODEL_SOURCE_CHECK", "True")

MAX_SIDE = 4000                 # hard cap before any engine sees the page
MIN_SIDE = 2000                 # smaller pages are upscaled (low-res screenshots)
OSD_MIN_CONFIDENCE = 2.0        # tesseract orientation confidence needed to rotate


@dataclass
class EngineResult:
    name: str
    ok: bool
    text: str = ""
    seconds: float = 0.0
    error: Optional[str] = None
    confidence: Optional[float] = None     # mean per-line confidence, 0..1, when the engine reports it
    lines: List[str] = field(default_factory=list)

    def summary(self) -> dict:
        return {
            "name": self.name,
            "ok": self.ok,
            "chars": len(self.text),
            "seconds": round(self.seconds, 2),
            "confidence": None if self.confidence is None else round(self.confidence, 2),
            "error": self.error,
        }


def _downscale(img: Image.Image, max_side: int) -> Image.Image:
    if max(img.size) <= max_side:
        return img
    img = img.copy()
    img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return img


def prepare_image(image_bytes: bytes) -> Image.Image:
    """Decode once for every engine: honour EXIF rotation, flatten transparency, force RGB."""
    with Image.open(io.BytesIO(image_bytes)) as src:
        img = ImageOps.exif_transpose(src)
        if img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            background = Image.new("RGB", rgba.size, "white")
            background.paste(rgba, mask=rgba.split()[-1])
            img = background
        else:
            img = img.convert("RGB")   # also handles CMYK JPEGs and 16-bit PNGs
    img = _downscale(img, MAX_SIDE)
    if max(img.size) < MIN_SIDE:
        # Small screenshots / thumbnails: upscale so thin ID characters span enough pixels
        scale = MIN_SIDE / max(img.size)
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS)
    return fix_orientation(img)


def fix_orientation(img: Image.Image) -> Image.Image:
    """Rotate scans / photos that are sideways or upside down (tesseract OSD)."""
    try:
        import pytesseract
        probe = _downscale(img, 1600)
        osd = pytesseract.image_to_osd(probe, output_type=pytesseract.Output.DICT)
        rotate = int(osd.get("rotate", 0))
        if rotate and float(osd.get("orientation_conf", 0)) >= OSD_MIN_CONFIDENCE:
            logger.info(f"Page is rotated; correcting by {rotate} degrees")
            return img.rotate(-rotate, expand=True, fillcolor="white")
    except Exception as e:  # too little text for OSD, or osd.traineddata missing
        logger.debug(f"Orientation detection skipped: {e}")
    return img


def _lines_to_text(lines: List[str]) -> str:
    return "\n".join(l for l in (s.strip() for s in lines) if l)


class OCREngine:
    name = "base"
    #: engines needing the original PDF rather than the rendered image
    needs_pdf = False

    def __init__(self):
        self._lock = threading.Lock()

    def available(self) -> bool:
        return True

    def load(self) -> None:
        """Load models (called lazily, and once at startup when warm-up is enabled)."""

    def run(self, img: Image.Image, pdf_bytes: Optional[bytes] = None) -> EngineResult:
        start = time.time()
        try:
            with self._lock:   # models are not guaranteed thread-safe
                lines, conf = self._recognise(img, pdf_bytes)
            text = _lines_to_text(lines)
            return EngineResult(self.name, ok=bool(text.strip()), text=text, lines=lines,
                                confidence=conf, seconds=time.time() - start,
                                error=None if text.strip() else "no text found")
        except Exception as e:
            logger.warning(f"OCR engine {self.name} failed: {e}")
            return EngineResult(self.name, ok=False, seconds=time.time() - start, error=str(e)[:200])

    def _recognise(self, img: Image.Image, pdf_bytes: Optional[bytes]) -> Tuple[List[str], Optional[float]]:
        raise NotImplementedError


class TesseractEngine(OCREngine):
    name = "tesseract"

    def available(self) -> bool:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def _recognise(self, img, pdf_bytes=None):
        import cv2
        import pytesseract

        gray = img.convert("L")
        if max(gray.size) < 1800:   # tesseract wants ~300 dpi text height
            gray = gray.resize((gray.width * 2, gray.height * 2), Image.Resampling.LANCZOS)

        # Pass 1: automatic page segmentation on the plain greyscale page
        lines = pytesseract.image_to_string(gray, lang="eng", config="--psm 3").splitlines()

        # Pass 2: local (adaptive) binarisation recovers light-grey IDs on white, sparse-text mode
        arr = np.array(gray)
        binary = cv2.adaptiveThreshold(arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
        sparse = pytesseract.image_to_string(Image.fromarray(binary), lang="eng", config="--psm 11").splitlines()

        seen = {" ".join(l.split()).lower() for l in lines}
        lines += [l for l in sparse if l.strip() and " ".join(l.split()).lower() not in seen]
        return lines, None


class PaddleEngine(OCREngine):
    name = "paddle"
    MAX_SIDE = 2400

    def __init__(self):
        super().__init__()
        self._ocr = None

    def available(self) -> bool:
        try:
            import paddleocr  # noqa: F401
            return True
        except Exception:
            return False

    def load(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(
                lang="en",
                text_detection_model_name="PP-OCRv5_mobile_det",
                text_recognition_model_name="en_PP-OCRv5_mobile_rec",
                use_doc_orientation_classify=False,   # orientation is fixed once, up front
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )

    def _recognise(self, img, pdf_bytes=None):
        self.load()
        arr = np.array(_downscale(img, self.MAX_SIDE))[:, :, ::-1]   # RGB -> BGR
        result = self._ocr.predict(arr)
        if not result:
            return [], None
        page = result[0]
        texts, scores = list(page["rec_texts"]), list(page["rec_scores"])
        kept = [(t, s) for t, s in zip(texts, scores) if t.strip() and s >= 0.3]
        conf = float(np.mean([s for _, s in kept])) if kept else None
        return [t for t, _ in kept], conf


class EasyOCREngine(OCREngine):
    name = "easyocr"
    MAX_SIDE = 2000   # CRAFT cost grows with area; 2000px keeps small IDs legible

    def __init__(self):
        super().__init__()
        self._reader = None

    def available(self) -> bool:
        try:
            import easyocr  # noqa: F401
            return True
        except Exception:
            return False

    def load(self):
        if self._reader is None:
            import easyocr
            self._reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    def _recognise(self, img, pdf_bytes=None):
        self.load()
        results = self._reader.readtext(np.array(_downscale(img, self.MAX_SIDE)))
        kept = [(bbox, t, c) for bbox, t, c in results if t.strip() and c >= 0.2]
        # Reading order: top-to-bottom, then left-to-right
        kept.sort(key=lambda r: (round(r[0][0][1] / 25), r[0][0][0]))
        conf = float(np.mean([c for _, _, c in kept])) if kept else None
        return [t for _, t, _ in kept], conf


class MistralOCREngine(OCREngine):
    """Cloud OCR. Opt-in via OCR_ENGINES because the page image leaves the server."""
    name = "mistral"
    MAX_SIDE = 2400

    def available(self) -> bool:
        return bool(config.MISTRAL_API_KEY)

    def _recognise(self, img, pdf_bytes=None):
        from mistralai import Mistral
        buf = io.BytesIO()
        _downscale(img, self.MAX_SIDE).save(buf, format="JPEG", quality=90)
        data_uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
        client = Mistral(api_key=config.MISTRAL_API_KEY, timeout_ms=config.OCR_ENGINE_TIMEOUT * 1000)
        resp = client.ocr.process(model=config.MISTRAL_OCR_MODEL,
                                  document={"type": "image_url", "image_url": data_uri})
        markdown = "\n".join(p.markdown for p in resp.pages)
        # Drop markdown decoration so it reads like the other engines' plain text
        lines = [l.lstrip("#>*-| ").replace("**", "").replace("|", " ") for l in markdown.splitlines()]
        return lines, None


class PdfTextEngine(OCREngine):
    """Text embedded in a digital PDF. Exact when present, but it is not what the reader
    sees, so it only counts as one vote and a disagreement with the image is reported."""
    name = "pdf_text"
    needs_pdf = True

    def available(self) -> bool:
        from shutil import which
        return which("pdftotext") is not None

    def _recognise(self, img, pdf_bytes=None):
        if not pdf_bytes:
            return [], None
        proc = subprocess.run(
            ["pdftotext", "-f", "1", "-l", "1", "-raw", "-enc", "UTF-8", "-", "-"],
            input=pdf_bytes, capture_output=True, timeout=20, check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.decode(errors="ignore")[:200] or "pdftotext failed")
        text = proc.stdout.decode("utf-8", errors="ignore")
        return [" ".join(l.split()) for l in text.splitlines()], None


ENGINE_CLASSES = {cls.name: cls for cls in (TesseractEngine, PaddleEngine, EasyOCREngine, MistralOCREngine, PdfTextEngine)}
