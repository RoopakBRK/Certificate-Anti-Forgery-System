"""
app/agents/ocr/consensus.py
Cross-engine voting on the fields that decide a verification: the certificate ID,
the printed verification URL and the holder's name.

A value read identically by several independent engines is far more likely to be
what is printed than any single engine's output (each engine makes different mistakes).
"""
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Pattern, Set, Tuple

from app.agents.verification.matching import name_match_score, normalize_id

# Characters OCR engines commonly confuse, mapped to what a hex ID can contain.
# "/" for "7" is applied in a separate variant so URL paths ("ude.my/UC-...") stay intact.
_CONFUSABLES = {"l": "1", "I": "1", "i": "1", "|": "1", "!": "1", "o": "0", "O": "0",
                "s": "5", "S": "5", "g": "9", "q": "9", "z": "2", "Z": "2"}
_HEX_REPAIR_KEEP_SLASH = str.maketrans(_CONFUSABLES)
_HEX_REPAIR = str.maketrans({**_CONFUSABLES, "/": "7"})

# "Certificate no: X", "Credential ID X", "Certification code: X", "Serial No. X" ...
# ("Reference Number" is deliberately absent: on Udemy it is a 4-digit non-unique number.)
_LABELLED_ID = re.compile(
    r"(?:certificate|certification|credential|cert|serial|registration|verification|validation|license|licence)"
    r"\s*(?:no|number|id|code|#)?\s*[.:#]?\s*[:#]?\s*"
    r"([A-Za-z0-9][A-Za-z0-9_-]{5,}(?:[\s-][A-Za-z0-9]{4,})*)",
    re.I,
)
_URL = re.compile(r"(?:https?\s*:\s*/\s*/\s*)?(?:www\.)?(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/[^\s,;\"'<>]*)?", re.I)
_GENERIC_ALNUM = re.compile(r"^[A-Za-z0-9]+$")


@dataclass
class Candidate:
    value: str
    engines: Set[str] = field(default_factory=set)
    exact_engines: Set[str] = field(default_factory=set)   # read without any repair
    occurrences: int = 0
    labelled: bool = False
    issuers: Set[str] = field(default_factory=set)          # issuer ID formats it matches

    @property
    def votes(self) -> int:
        return len(self.engines)

    def to_dict(self, engine_count: int) -> dict:
        return {
            "value": self.value,
            "votes": self.votes,
            "engines": sorted(self.engines),
            "agreement": round(self.votes / engine_count, 2) if engine_count else 0.0,
        }


def _id_key(value: str) -> str:
    return normalize_id(value)


def _is_plausible_id(value: str, distinctive: bool) -> bool:
    """Reject words ("CERTIFICATE") and bare short numbers that are never certificate IDs."""
    core = normalize_id(value)
    if len(core) < 6:
        return False
    if distinctive:
        return True
    has_digit = any(c.isdigit() for c in core)
    has_alpha = any(c.isalpha() for c in core)
    return has_digit and (has_alpha or len(core) >= 8)


def _hex_like(pattern: Pattern) -> bool:
    return "[0-9a-f]" in pattern.pattern


def _glue_split_ids(text: str) -> str:
    """Rejoin IDs broken around hyphens or across lines: 'UC-9ba4 - 3983' -> 'UC-9ba4-3983'."""
    return re.sub(r"(?<=[A-Za-z0-9])\s*-\s*(?=[A-Za-z0-9])", "-", text)


class Consensus:
    def __init__(self, engine_texts: Dict[str, str], id_patterns: Iterable[Tuple[str, Pattern]],
                 distinctive: Optional[Set[str]] = None):
        """
        engine_texts: {engine name: text} for every engine that produced text
        id_patterns:  (issuer name, compiled regex) pairs from the issuer registry
        distinctive:  issuer names whose ID format is distinctive (e.g. "UC-<uuid>")
        """
        self.engine_texts = {k: v for k, v in engine_texts.items() if v and v.strip()}
        self.engine_count = len(self.engine_texts)
        self.id_patterns = list(id_patterns)
        self.distinctive = distinctive or set()
        self._ids: Dict[str, Candidate] = {}
        self._urls: Dict[str, Candidate] = {}
        for engine, text in self.engine_texts.items():
            self._collect(engine, text)

    # --- Collection ----------------------------------------------------------

    def _add(self, store: Dict[str, Candidate], key: str, value: str, engine: str, exact: bool,
             labelled: bool = False, issuer: Optional[str] = None) -> None:
        cand = store.get(key)
        if cand is None:
            cand = store[key] = Candidate(value=value)
        cand.engines.add(engine)
        if exact:
            cand.exact_engines.add(engine)
            cand.value = value if len(cand.exact_engines) == 1 else cand.value
        cand.occurrences += 1
        cand.labelled |= labelled
        if issuer:
            cand.issuers.add(issuer)

    def _collect(self, engine: str, text: str) -> None:
        glued = _glue_split_ids(text)
        tokens = glued.split()

        # 1. Issuer-specific ID formats, on the raw tokens and on OCR-repaired tokens
        for issuer, pattern in self.id_patterns:
            hex_like = _hex_like(pattern)
            finder = re.compile(rf"(?<![A-Za-z0-9])(?:{pattern.pattern})(?![A-Za-z0-9])", re.I if hex_like else 0)
            distinctive = issuer in self.distinctive
            for tok in tokens:
                variants = [(tok, True)]
                if hex_like:
                    variants += [(tok.translate(_HEX_REPAIR_KEEP_SLASH), False), (tok.translate(_HEX_REPAIR), False)]
                for variant, exact in variants:
                    for m in finder.finditer(variant):
                        value = m.group(0)
                        if not _is_plausible_id(value, distinctive):
                            continue
                        if hex_like:   # canonical case: lower-case hex, upper-case literal prefix ("UC-")
                            prefix = re.match(r"[A-Za-z]+-", value)
                            value = (prefix.group(0).upper() + value[prefix.end():].lower()) if prefix else value.lower()
                        self._add(self._ids, _id_key(value), value, engine, exact, issuer=issuer)

        # 2. IDs introduced by a label ("Certificate no: ...", "Credential ID ...")
        for m in _LABELLED_ID.finditer(glued):
            value = re.sub(r"\s+", "", m.group(1)).strip("-_")
            if _is_plausible_id(value, distinctive=False):
                self._add(self._ids, _id_key(value), value, engine, exact=True, labelled=True)

        # 3. Verification URLs
        for m in _URL.finditer(glued):
            url = re.sub(r"\s+", "", m.group(0)).rstrip(".)")
            if "/" not in url.split("://")[-1]:
                continue  # bare domains ("coursera.org") are not verification links
            if not re.match(r"https?://", url, re.I):
                url = "https://" + url
            self._add(self._urls, url.lower(), url, engine, exact=True)
            # the last path segment of a verification URL is usually the ID
            tail = url.rstrip("/").rsplit("/", 1)[-1].split("?")[0]
            if _is_plausible_id(tail, distinctive=False):
                self._add(self._ids, _id_key(tail), tail, engine, exact=True, labelled=True)

    # --- Queries -------------------------------------------------------------

    def _score(self, c: Candidate, issuer_name: Optional[str]) -> float:
        return (
            c.votes * 10
            + len(c.exact_engines) * 2
            + (8 if issuer_name and issuer_name in c.issuers else 0)
            + (4 if c.issuers & self.distinctive else 0)
            + (3 if c.labelled else 0)
            + min(c.occurrences, 6) * 0.5
            + min(len(normalize_id(c.value)), 40) / 20
        )

    def id_candidates(self, issuer_name: Optional[str] = None, id_regex: Optional[Pattern] = None) -> List[Candidate]:
        """ID candidates ranked best-first. With an issuer, only IDs in its format are returned."""
        cands = list(self._ids.values())
        if id_regex is not None:
            cands = [c for c in cands if id_regex.fullmatch(c.value)]
        else:
            cands = [c for c in cands if c.labelled or c.issuers & self.distinctive or c.votes >= 2]
        return sorted(cands, key=lambda c: self._score(c, issuer_name), reverse=True)

    def best_id(self, issuer_name: Optional[str] = None, id_regex: Optional[Pattern] = None) -> Optional[Candidate]:
        ranked = self.id_candidates(issuer_name, id_regex)
        return ranked[0] if ranked else None

    def support_for_id(self, value: Optional[str]) -> Set[str]:
        """Engines whose text contains this ID (separator-insensitive, after OCR repair)."""
        if not value:
            return set()
        key = _id_key(value)
        if len(key) < 6:
            return set()
        engines = set(self._ids[key].engines) if key in self._ids else set()
        for engine, text in self.engine_texts.items():
            flat = normalize_id(text)
            if key in flat or key in normalize_id(text.translate(_HEX_REPAIR)) \
                    or key in normalize_id(text.translate(_HEX_REPAIR_KEEP_SLASH)):
                engines.add(engine)
        return engines

    def urls(self) -> List[Candidate]:
        return sorted(self._urls.values(), key=lambda c: (c.votes, len(c.value)), reverse=True)

    def support_for_name(self, name: Optional[str]) -> Set[str]:
        """Engines in whose text every token of the name appears close together."""
        if not name:
            return set()
        return {engine for engine, text in self.engine_texts.items() if name_match_score(name, text)[0]}
