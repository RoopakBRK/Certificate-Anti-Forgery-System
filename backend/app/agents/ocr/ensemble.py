"""
app/agents/ocr/ensemble.py
Runs every enabled OCR engine on the same page in parallel and builds a Consensus.

Each engine gets its own single-worker thread pool: engines run concurrently with each
other, a slow or crashed engine never blocks the rest, and a timed-out engine cannot
pile up abandoned jobs (its next job simply queues behind it).
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

from app.config import config
from app.agents.verification.sources import default_registry, _is_distinctive
from .consensus import Consensus
from .engines import ENGINE_CLASSES, EngineResult, OCREngine, prepare_image

logger = logging.getLogger(__name__)


@dataclass
class EnsembleResult:
    image: Image.Image
    results: List[EngineResult]
    consensus: Consensus
    qr_codes: List[str] = field(default_factory=list)
    # The vision model's reading (a VLMReading). Started with the engines, possibly still running.
    vlm_task: Optional[asyncio.Task] = None

    @property
    def ok_results(self) -> List[EngineResult]:
        return [r for r in self.results if r.ok]

    @property
    def image_engine_texts(self) -> Dict[str, str]:
        """Text read from the pixels (what a human sees), excluding the PDF text layer."""
        return {r.name: r.text for r in self.ok_results if r.name != "pdf_text"}

    def combined_text(self) -> str:
        return "\n".join(r.text for r in self.ok_results)


def decode_qr_codes(img: Image.Image) -> List[str]:
    """Try several scales/binarisations: certificate QR codes are often small and low-contrast."""
    import cv2
    found: List[str] = []
    detector = cv2.QRCodeDetector()
    bgr = np.array(img)[:, :, ::-1].copy()
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    variants = [bgr, gray]
    if max(gray.shape) < 2500:
        variants.append(cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC))
    else:
        variants.append(cv2.resize(gray, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA))
    variants.append(cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1])
    for variant in variants:
        try:
            ok, decoded, _, _ = detector.detectAndDecodeMulti(variant)
            if ok:
                found += [d for d in decoded if d]
            else:
                data, _, _ = detector.detectAndDecode(variant)
                if data:
                    found.append(data)
        except cv2.error as e:
            logger.debug(f"QR decode variant failed: {e}")
        if found:
            break
    return list(dict.fromkeys(found))


class OCREnsemble:
    def __init__(self, engine_names: Optional[List[str]] = None, vlm=None):
        names = engine_names or config.OCR_ENGINES
        self.vlm = vlm   # optional VLMReader; it reads beside the engines and is not waited for
        self.engines: List[OCREngine] = []
        for name in names:
            cls = ENGINE_CLASSES.get(name)
            if cls is None:
                logger.warning(f"Unknown OCR engine {name!r} in OCR_ENGINES; ignoring")
                continue
            engine = cls()
            if engine.available():
                self.engines.append(engine)
            else:
                logger.warning(f"OCR engine {name!r} is not installed/configured; skipping")
        # The PDF text layer is free and exact for digital PDFs, so it always takes part
        if not any(e.name == "pdf_text" for e in self.engines):
            pdf = ENGINE_CLASSES["pdf_text"]()
            if pdf.available():
                self.engines.append(pdf)
        if not any(not e.needs_pdf for e in self.engines):
            raise RuntimeError("No OCR engine is available. Install tesseract, paddleocr or easyocr.")
        self._pools = {e.name: ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"ocr-{e.name}")
                       for e in self.engines}
        registry = default_registry()
        self._id_patterns = registry.id_patterns()
        self._distinctive = {name for name, rx in self._id_patterns if _is_distinctive(rx)}
        logger.info(f"OCR ensemble engines: {[e.name for e in self.engines]}")

    @property
    def engine_names(self) -> List[str]:
        return [e.name for e in self.engines]

    async def warmup(self) -> None:
        """Load models in the background so the first real request is not slow."""
        loop = asyncio.get_running_loop()
        for engine in self.engines:
            try:
                await loop.run_in_executor(self._pools[engine.name], engine.load)
                logger.info(f"OCR engine {engine.name} ready")
            except Exception as e:
                logger.warning(f"OCR engine {engine.name} failed to load: {e}")

    async def _run_engine(self, engine: OCREngine, img: Image.Image, pdf_bytes: Optional[bytes]) -> EngineResult:
        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(self._pools[engine.name], engine.run, img, pdf_bytes)
        try:
            return await asyncio.wait_for(fut, timeout=config.OCR_ENGINE_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning(f"OCR engine {engine.name} timed out after {config.OCR_ENGINE_TIMEOUT}s")
            return EngineResult(engine.name, ok=False, seconds=float(config.OCR_ENGINE_TIMEOUT), error="timeout")

    async def run(self, image_bytes: bytes, pdf_bytes: Optional[bytes] = None) -> EnsembleResult:
        img = await asyncio.to_thread(prepare_image, image_bytes)
        # The vision model gets the whole OCR run as a head start; only the engines are awaited
        vlm_task = asyncio.create_task(self.vlm.read(img)) if self.vlm else None
        engines = [e for e in self.engines if not e.needs_pdf or pdf_bytes]
        results, qr_codes = await asyncio.gather(
            asyncio.gather(*(self._run_engine(e, img, pdf_bytes) for e in engines)),
            asyncio.to_thread(decode_qr_codes, img),
        )
        for r in results:
            level = logging.INFO if r.ok else logging.WARNING
            logger.log(level, f"OCR {r.name}: ok={r.ok} chars={len(r.text)} {r.seconds:.1f}s {r.error or ''}")
        texts = {r.name: r.text for r in results if r.ok}
        # QR payloads are machine-read and exact: they vote like an engine
        if qr_codes:
            texts["qr"] = "\n".join(qr_codes)
        consensus = Consensus(texts, self._id_patterns, self._distinctive)
        return EnsembleResult(image=img, results=list(results), consensus=consensus, qr_codes=qr_codes,
                              vlm_task=vlm_task)
