"""
app/agents/verification/visual.py
Handles visual fallback: Reading text from screenshots when DOM scraping fails.
"""
import logging
from PIL import Image
import pytesseract
from typing import Tuple

from .matching import name_match_score, id_in_text

logger = logging.getLogger(__name__)

class VisualVerifier:
    def __init__(self):
        # Verify tesseract is available
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            logger.warning("⚠️ Tesseract OCR not found. Visual verification will be disabled.")

    def _ocr(self, image_path: str) -> str:
        with Image.open(image_path) as img:
            # --psm 6 assumes a block of text, good for documents
            return pytesseract.image_to_string(img, config='--psm 6')

    def verify_screenshot(self, image_path: str, candidate_name: str) -> Tuple[bool, float, str]:
        """OCR the screenshot and match the candidate name (all name tokens, close together)."""
        if not image_path:
            return False, 0.0, ""
        try:
            extracted_text = self._ocr(image_path)
            is_match, score = name_match_score(candidate_name, extracted_text)
            return is_match, score, extracted_text
        except Exception as e:
            logger.error(f"Visual verification failed: {e}")
            return False, 0.0, ""

    def verify_screenshot_id(self, image_path: str, certificate_id: str) -> Tuple[bool, float, str]:
        """OCR the screenshot and look for the certificate ID (separator-insensitive, exact)."""
        if not image_path:
            return False, 0.0, ""
        try:
            extracted_text = self._ocr(image_path)
            found = id_in_text(certificate_id, extracted_text)
            return found, 1.0 if found else 0.0, extracted_text
        except Exception as e:
            logger.error(f"Visual ID verification failed: {e}")
            return False, 0.0, ""
