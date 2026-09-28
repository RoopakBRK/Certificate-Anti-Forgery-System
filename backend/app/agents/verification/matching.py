"""
app/agents/verification/matching.py
Pure text-matching helpers used by the verification service (easy to unit-test).
"""
import re
import unicodedata
from difflib import SequenceMatcher
from typing import List, Tuple

TOKEN_SIMILARITY = 0.85      # per-token fuzzy threshold (tolerates OCR slips)
WINDOW_SLACK = 4             # extra words allowed between name tokens
MIN_ID_LENGTH = 8

_BLOCK_MARKERS = (
    "captcha", "verify you are human", "are you a robot", "access denied",
    "just a moment", "enable javascript", "checking your browser",
    "unusual traffic", "403 forbidden", "sign in to continue", "log in to continue",
    "please log in", "please sign in",
)


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def tokenize(text: str) -> List[str]:
    text = _strip_accents(text or "").lower()
    return re.findall(r"[a-z0-9]+", text)


def normalize_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def name_match_score(candidate: str, page_text: str) -> Tuple[bool, float]:
    """
    Score how well `candidate` appears in `page_text` as a name.

    All name tokens must be found close together (a sliding window over the page words),
    so a common first name appearing anywhere on the page is not a match. Names with a
    single token can never be verified (too ambiguous): they score at most 0.5.
    """
    name_tokens = tokenize(candidate)
    page_tokens = tokenize(page_text)
    if not name_tokens or not page_tokens:
        return False, 0.0

    n = len(name_tokens)
    window = n + WINDOW_SLACK
    best = 0.0

    # Index page positions that are (fuzzily) equal to each name token
    hits = []
    for tok in name_tokens:
        positions = [
            i for i, w in enumerate(page_tokens)
            if w == tok or (len(tok) > 3 and SequenceMatcher(None, tok, w).ratio() >= TOKEN_SIMILARITY)
        ]
        hits.append(positions)

    if not any(hits):
        return False, 0.0

    # Candidate window starts come from any hit position
    starts = {max(0, p - window + 1) for positions in hits for p in positions}
    for start in starts:
        lo, hi = start, start + window
        found = sum(1 for positions in hits if any(lo <= p < hi for p in positions))
        best = max(best, found / n)
        if best == 1.0:
            break

    if n < 2:
        return False, min(best, 0.5)
    return best == 1.0, round(best, 2)


def id_in_text(cert_id: str, text: str) -> bool:
    """Exact (separator-insensitive) containment of a certificate ID in page text."""
    cid = normalize_id(cert_id)
    if len(cid) < MIN_ID_LENGTH:
        return False
    return cid in normalize_id(text)


def looks_blocked(text: str) -> bool:
    """Heuristic: bot wall / login wall / JS shell rather than real certificate content."""
    if not text:
        return True
    lowered = text.lower()
    if len(lowered.strip()) < 500 and any(m in lowered for m in _BLOCK_MARKERS):
        return True
    # Long pages that are mostly a challenge notice
    return sum(m in lowered for m in _BLOCK_MARKERS) >= 2 and len(lowered) < 3000
