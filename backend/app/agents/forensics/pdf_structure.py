"""
app/agents/forensics/pdf_structure.py
Structural PDF forensics.

Platform certificates such as Udemy's are exported as a single full-page image with no
text layer. Editing one in a PDF editor (to change a name or date) leaves the original
image untouched and draws new text ON TOP of it, adding a font and a tiny text layer.
Pixel forensics cannot see that edit, but the PDF structure gives it away.
"""
import logging
import re
import subprocess
from typing import List, Optional

logger = logging.getLogger(__name__)

FULL_PAGE_COVERAGE = 0.8        # an image covering >= 80% of the page is "the certificate"
OVERLAY_MAX_WORDS = 15          # a partial overlay is a few words, not the whole certificate
OVERLAY_MAX_RATIO = 0.35        # ... and far less than what OCR reads on the page


def _run(args: List[str], pdf_bytes: bytes) -> str:
    proc = subprocess.run(args, input=pdf_bytes, capture_output=True, timeout=20, check=False)
    return proc.stdout.decode("utf-8", errors="ignore") if proc.returncode == 0 else ""


def _page_size_pt(info: str) -> Optional[tuple]:
    # "Page size:" or, with -f/-l, "Page    1 size:"
    m = re.search(r"Page\s+(?:\d+\s+)?size:\s+([\d.]+)\s+x\s+([\d.]+)\s+pts", info)
    return (float(m.group(1)), float(m.group(2))) if m else None


def _modified_after_creation(info: str) -> Optional[str]:
    """Informational: incremental saves (e.g. macOS Preview "AppendMode") or a later ModDate."""
    producer = re.search(r"^Producer:\s*(.+)$", info, re.M)
    created = re.search(r"^CreationDate:\s*(.+)$", info, re.M)
    modified = re.search(r"^ModDate:\s*(.+)$", info, re.M)
    if producer and "appendmode" in producer.group(1).lower():
        return f"The PDF was re-saved after creation ({producer.group(1).strip()})."
    if created and modified and created.group(1).strip() != modified.group(1).strip():
        return f"The PDF was modified after creation (created {created.group(1).strip()}, modified {modified.group(1).strip()})."
    return None


def _largest_image_coverage(pdf_bytes: bytes, page: tuple) -> float:
    """Fraction of page 1 covered by its largest raster image (from pdfimages -list)."""
    listing = _run(["pdfimages", "-f", "1", "-l", "1", "-list", "-"], pdf_bytes)
    best = 0.0
    for line in listing.splitlines()[2:]:
        cols = line.split()
        # page num type width height color comp bpc enc interp object ID x-ppi y-ppi size ratio
        if len(cols) < 14 or cols[2] != "image":
            continue
        try:
            width, height, xppi, yppi = int(cols[3]), int(cols[4]), float(cols[12]), float(cols[13])
        except ValueError:
            continue
        if xppi <= 0 or yppi <= 0:
            continue
        area = (width / xppi * 72) * (height / yppi * 72)
        best = max(best, area / (page[0] * page[1]))
    return best


def analyze_pdf(pdf_bytes: bytes, visible_words: int) -> dict:
    """Returns {"suspicious": bool, "details": [...], "notes": [...], "overlay_text": str | None}.

    `details` are tamper findings; `notes` are informational (a re-saved PDF is not proof of forgery).
    """
    result = {"suspicious": False, "details": [], "notes": [], "overlay_text": None}
    try:
        info = _run(["pdfinfo", "-f", "1", "-l", "1", "-"], pdf_bytes)
        note = _modified_after_creation(info)
        if note:
            result["notes"].append(note)
        page = _page_size_pt(info)
        if not page:
            return result
        text_layer = " ".join(_run(["pdftotext", "-f", "1", "-l", "1", "-raw", "-", "-"], pdf_bytes).split())
        layer_words = len(text_layer.split())
        if layer_words == 0:
            return result
        coverage = _largest_image_coverage(pdf_bytes, page)
        visible_words = max(visible_words, 1)   # words OCR read from the rendered page
        if (coverage >= FULL_PAGE_COVERAGE and layer_words <= OVERLAY_MAX_WORDS
                and layer_words <= OVERLAY_MAX_RATIO * visible_words):
            snippet = text_layer[:80]
            result.update(
                suspicious=True,
                overlay_text=snippet,
                details=[f'PDF edit detected: the text "{snippet}" was typed on top of the certificate image. '
                         "Genuine exports of this kind contain the image only; an added text layer is how "
                         "names, dates or IDs are altered in a PDF editor."],
            )
    except Exception as e:
        logger.warning(f"PDF structure analysis failed: {e}")
    return result
