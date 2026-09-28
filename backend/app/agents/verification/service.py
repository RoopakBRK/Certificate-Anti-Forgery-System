"""
app/agents/verification/service.py
Core verification service.

A certificate is VERIFIED only when the issuer page (a) is on a trusted host, and
(b) shows the candidate's full name close together, and (c) refers to the same
certificate ID (in the page text, or in the URL the page was fetched from).
"""
import logging
from typing import Optional

from app.schemas import ExtractionResult, VerificationResult
from .sources import TrustedSourceRegistry
from .scanner import fetch_page_text
from .visual import VisualVerifier
from .matching import name_match_score, id_in_text, normalize_id, MIN_ID_LENGTH

logger = logging.getLogger(__name__)


class VerificationService:
    def __init__(self):
        self.registry = TrustedSourceRegistry()
        self.visual = VisualVerifier()

    @staticmethod
    def _id_confirmed(cert_id: Optional[str], url: str, page_text: Optional[str]) -> bool:
        """The page must belong to this certificate: ID in the text or in the fetched URL."""
        if not cert_id or len(normalize_id(cert_id)) < MIN_ID_LENGTH:
            return False
        return id_in_text(cert_id, page_text or "") or normalize_id(cert_id) in normalize_id(url)

    async def verify(self, data: ExtractionResult) -> VerificationResult:
        # A. Validation
        if not data.candidate_name:
            return VerificationResult(is_verified=False, trusted_domain=False, message="No candidate name.", method="validation_error")
        if not data.certificate_id:
            return VerificationResult(is_verified=False, trusted_domain=False, message="No certificate ID could be read from the document.", method="validation_error")

        # B. Get URLs
        org_name_str = data.issuer_name.value if data.issuer_name else (data.issuer_org or "")
        urls = self.registry.generate_urls(data.issuer_url, data.certificate_id, org_name_str)
        if not urls:
            return VerificationResult(is_verified=False, trusted_domain=False, message="No URL generated.", method="url_error")

        # C. Trust Check: every URL that will be fetched must be on a trusted host
        untrusted = urls[0] if not self.registry.is_trusted(urls[0]) else None
        urls = [u for u in urls if self.registry.is_trusted(u)]
        if not urls:
            return VerificationResult(is_verified=False, trusted_domain=False, verification_url=untrusted, message="Untrusted domain.", method="security_check")

        # D. Verification loop
        best_score = 0.0
        best_url = urls[0]
        name_ok_without_id = False

        for url in urls[:2]:
            logger.info(f"Scanning: {url}")

            # fetch_page_text falls back to the browser itself when the fast fetch is empty or blocked
            page_text, screenshot_path = await fetch_page_text(url, use_browser=True, force_browser=False)

            # 1. Text match
            if page_text:
                is_match, score = name_match_score(data.candidate_name, page_text)
                best_score = max(best_score, score)
                if is_match:
                    if self._id_confirmed(data.certificate_id, url, page_text):
                        return VerificationResult(is_verified=True, trusted_domain=True, confidence_score=score, verification_url=url, method="dom_text_match", message=f"Verified via text. Name match: {score:.0%}")
                    name_ok_without_id = True

            # 2. The fast fetch was a plain HTTP response that did not match: render it in a browser
            if not screenshot_path and best_score < 1.0:
                logger.info("Text match failed on fast fetch. Forcing browser retry...")
                page_text, screenshot_path = await fetch_page_text(url, force_browser=True)
                if page_text:
                    is_match, score = name_match_score(data.candidate_name, page_text)
                    best_score = max(best_score, score)
                    if is_match:
                        if self._id_confirmed(data.certificate_id, url, page_text):
                            return VerificationResult(is_verified=True, trusted_domain=True, confidence_score=score, verification_url=url, method="dom_text_match_retry", message=f"Verified via browser text. Name match: {score:.0%}")
                        name_ok_without_id = True

            # 3. Visual fallback (OCR of the screenshot)
            if screenshot_path:
                v_match, v_score, v_text = self.visual.verify_screenshot(screenshot_path, data.candidate_name)
                best_score = max(best_score, v_score)
                if v_match:
                    if self._id_confirmed(data.certificate_id, url, v_text):
                        return VerificationResult(is_verified=True, trusted_domain=True, confidence_score=v_score, verification_url=url, method="visual_ocr", message=f"Verified via visual OCR. Name match: {v_score:.0%}")
                    name_ok_without_id = True

        if name_ok_without_id:
            message = "The name was found on the issuer page, but the certificate ID could not be confirmed."
        else:
            message = f"Verification failed. Best name match: {best_score:.0%}"
        return VerificationResult(is_verified=False, trusted_domain=True, confidence_score=best_score, verification_url=best_url, method="failed", message=message)

    async def manual_verify(self, certificate_id: str, issuer_url: str) -> VerificationResult:
        """
        Manually verifies a certificate using ID and URL provided by the user.
        The URL must be a trusted issuer domain; the certificate ID must appear on the page.
        """
        logger.info(f"Manual Verification: {certificate_id} @ {issuer_url}")

        if len(normalize_id(certificate_id)) < MIN_ID_LENGTH:
            return VerificationResult(is_verified=False, trusted_domain=False, verification_url=issuer_url, method="manual_failed", message=f"Certificate ID must be at least {MIN_ID_LENGTH} letters/digits to be checked reliably.")

        # Only issuer domains from the trusted registry may be used as proof
        if not self.registry.is_trusted(issuer_url):
            return VerificationResult(is_verified=False, trusted_domain=False, verification_url=issuer_url, method="security_check", message="URL is not a recognised issuer verification domain.")

        page_text, screenshot_path = await fetch_page_text(issuer_url, force_browser=True)

        if not page_text and not screenshot_path:
            logger.warning("Manual verify: No text and no screenshot.")
            return VerificationResult(is_verified=False, trusted_domain=True, verification_url=issuer_url, method="manual_failed", message="Could not fetch page content.")

        is_verified, confidence, method = False, 0.0, "manual_failed"
        message = "Certificate ID not found on page."

        if page_text and id_in_text(certificate_id, page_text):
            is_verified, confidence, method = True, 1.0, "manual_text_match"
            message = "Certificate ID found in page text."

        if not is_verified and screenshot_path:
            v_match, v_score, _ = self.visual.verify_screenshot_id(screenshot_path, certificate_id)
            if v_match:
                is_verified, confidence, method = True, v_score, "manual_visual_ocr"
                message = "Certificate ID found in screenshot."

        return VerificationResult(
            is_verified=is_verified,
            trusted_domain=True,
            confidence_score=confidence,
            verification_url=issuer_url,
            method=method,
            message=message
        )


# Singleton
_service_instance: Optional[VerificationService] = None
def get_verification_service() -> VerificationService:
    global _service_instance
    if _service_instance is None:
        _service_instance = VerificationService()
    return _service_instance
