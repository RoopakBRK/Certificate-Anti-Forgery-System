"""
ext.py
Extraction agent: parallel multi-engine OCR -> cross-engine consensus -> LLM structuring.

1. Every OCR engine (tesseract, PaddleOCR, EasyOCR, optionally Mistral OCR, plus the PDF
   text layer and QR codes) reads the page at the same time.
2. The consensus layer votes on certificate IDs and verification URLs across engines,
   repairing typical OCR confusions (l/1, O/0, "/"/7) inside hex IDs.
3. An LLM turns the texts into fields. Its answer is then checked against the votes: an ID
   that more engines agree on wins, and a name no engine actually read is rejected.
4. If the LLM is not configured or fails, deterministic heuristics fill the fields instead.
"""

import asyncio
import io
import json
import logging
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from PIL import Image

from app.config import config
from app.agents.ocr.ensemble import EnsembleResult, OCREnsemble
from app.agents.verification.matching import name_match_score, normalize_id
from app.agents.verification.sources import Issuer, default_registry

logger = logging.getLogger(__name__)
logger.setLevel(config.LOG_LEVEL)

MAX_IMAGE_SIZE_BYTES = 40 * 1024 * 1024   # rendered PDF pages can be large PNGs
MAX_TEXT_SNIPPET_LENGTH = 300
LLM_TIMEOUT_SECONDS = 30
PER_ENGINE_PROMPT_CHARS = 1500


class LLMHTTPError(Exception):
    """HTTP failure from an OpenAI-compatible provider (carries status_code for retry logic)."""
    def __init__(self, status_code: int, body: str):
        super().__init__(f"API error occurred: Status {status_code}. Body: {body[:300]}")
        self.status_code = status_code


# OpenAI-compatible chat endpoints
_OPENAI_COMPAT = {
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "huggingface": "https://router.huggingface.co/v1/chat/completions",
}

# Heuristic name extraction
_NAME_INTRO = re.compile(
    r"(?:this\s+is\s+to\s+certify\s+that|certify\s+that|certifies\s+that|awarded\s+to|presented\s+to|"
    r"conferred\s+(?:up)?on|granted\s+to|issued\s+to|proudly\s+presented\s+to)\s*[:,]?\s*(.*)$", re.I)
_NAME_OUTRO = re.compile(r"^\s*(?:has\s+)?(?:successfully\s+)?(?:completed|participated|achieved|passed|earned|fulfilled)\b", re.I)
_NAME_STOPWORDS = {
    "certificate", "certification", "completion", "course", "courses", "instructor", "instructors",
    "date", "length", "hours", "verify", "university", "academy", "program", "programme", "specialization",
    "professional", "online", "credential", "awarded", "achievement", "of", "the", "and", "in", "for",
    "reference", "number", "signature", "director", "ceo", "founder", "team",
}


def _clean_person_name(raw: str) -> Optional[str]:
    name = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ.'\- ]", " ", raw or "")
    name = " ".join(name.split()).strip(" .-'")
    words = name.split()
    if not 2 <= len(words) <= 5 or len(name) > 60:
        return None
    if any(w.lower().strip(".") in _NAME_STOPWORDS for w in words):
        return None
    if not all(len(w.strip(".")) >= 1 and w[0].isalpha() for w in words):
        return None
    return name.title() if name.isupper() or name.islower() else name


class ExtractionAgent:
    """Parallel multi-engine OCR + consensus + LLM extraction (LLM optional)."""

    def __init__(self, api_key: str = "", ensemble: Optional[OCREnsemble] = None):
        self.api_key = api_key
        self.provider = config.EXTRACTION_PROVIDER
        self.client = None
        if api_key and self.provider == "mistral":
            from mistralai import Mistral
            self.client = Mistral(api_key=api_key)
        self._ensemble = ensemble
        self.registry = default_registry()
        logger.info(f"Extraction agent initialized (provider={self.provider}, llm={'on' if api_key else 'off'})")

    @property
    def ensemble(self) -> OCREnsemble:
        if self._ensemble is None:
            self._ensemble = OCREnsemble()
        return self._ensemble

    @property
    def llm_available(self) -> bool:
        return bool(self.api_key)

    # --- LLM -----------------------------------------------------------------

    def _complete(self, prompt: str) -> str:
        """One chat completion via the configured provider; returns the message text."""
        if self.provider == "mistral":
            r = self.client.chat.complete(model=config.MISTRAL_MODEL, temperature=0,
                                          messages=[{"role": "user", "content": prompt}])
            return r.choices[0].message.content
        url = _OPENAI_COMPAT.get(self.provider)
        if url is None:
            raise ValueError(f"Unknown EXTRACTION_PROVIDER: {self.provider!r}")
        model = config.GROQ_MODEL if self.provider == "groq" else config.HF_MODEL
        body = {"model": model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}
        if self.provider == "groq":
            body["response_format"] = {"type": "json_object"}
            if "gpt-oss" in model:
                body["reasoning_effort"] = "low"   # field extraction needs no long reasoning
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=body,
            timeout=LLM_TIMEOUT_SECONDS,
        )
        if resp.status_code != 200:
            raise LLMHTTPError(resp.status_code, resp.text)
        return resp.json()["choices"][0]["message"]["content"]

    async def _call_llm(self, prompt: str) -> dict:
        """LLM call with retries on transient failures (429 / 5xx / timeout); returns parsed JSON."""
        response = None
        for attempt in range(3):
            try:
                response = await asyncio.wait_for(asyncio.to_thread(self._complete, prompt),
                                                  timeout=LLM_TIMEOUT_SECONDS)
                break
            except asyncio.TimeoutError:
                if attempt == 2:
                    raise TimeoutError(f"LLM API exceeded timeout of {LLM_TIMEOUT_SECONDS}s")
            except Exception as e:
                status = getattr(e, "status_code", None)
                if status not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise
                logger.warning(f"LLM transient error {status}, retrying...")
            await asyncio.sleep(2 ** attempt)
        return self._parse_json(response or "")

    @staticmethod
    def _parse_json(text: str) -> dict:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S) or re.search(r"\{.*\}", text, re.S)
            if not match:
                raise ValueError("Failed to parse LLM response as JSON")
            data = json.loads(match.group(1) if match.re.groups else match.group(0))
        if not isinstance(data, dict):
            raise ValueError("Extraction response was not a JSON object")
        return data

    def _build_prompt(self, ens: EnsembleResult) -> str:
        c = ens.consensus
        blocks = []
        for r in ens.ok_results:
            label = "PDF TEXT LAYER (embedded text, may differ from what is printed)" if r.name == "pdf_text" \
                else f"OCR ENGINE: {r.name}"
            blocks.append(f"--- {label} ---\n{r.text[:PER_ENGINE_PROMPT_CHARS]}")
        if ens.qr_codes:
            blocks.append("--- QR CODE PAYLOADS (machine-read, exact) ---\n" + "\n".join(ens.qr_codes))
        id_hints = "\n".join(f"  {x.value}  (read identically by {x.votes}/{c.engine_count} sources: {', '.join(sorted(x.engines))})"
                             for x in c.id_candidates()[:5]) or "  (none)"
        url_hints = "\n".join(f"  {u.value}  ({u.votes}/{c.engine_count})" for u in c.urls()[:3]) or "  (none)"

        return f"""You extract fields from a certificate. The same page was read by several independent OCR engines.
Each engine makes DIFFERENT mistakes, so prefer spellings that several engines agree on and never invent text.

Fields:
1. candidate_name: the person who RECEIVED the certificate (the learner), not an instructor, signatory or company.
   - Udemy: the learner's name is the line right after the instructor list, just before "Date".
   - Usually near "This is to certify that", "awarded to", or just before "has successfully completed".
2. certificate_id: the unique certificate / credential ID, as ONE string with no spaces.
   - Udemy: "UC-" + UUID. Ignore the 4-digit "Reference Number".
   - Coursera: 10-14 upper-case letters/digits (the last part of coursera.org/verify/...).
   - edX / Cognitive Class / NVIDIA / HubSpot: 32 hex characters. LinkedIn Learning: 64 hex. DataCamp: 40 hex.
   - NPTEL: starts with "NPTEL" (e.g. NPTEL25CS110S46360038410384681). Credly/Accredible: a UUID.
   - If only a short reference number exists, return "".
3. issuer_name: the platform that issued the certificate and hosts its verification (e.g. "Coursera", "Udemy",
   "edX", "NPTEL", "Credly"). "Authorized by Google and offered through Coursera" -> "Coursera".
4. issuer_url: the full verification URL printed on the certificate or in a QR code, else "".
5. certificate_date: the issue/completion date as printed, else "".

Candidate IDs found by cross-engine voting:
{id_hints}
Candidate verification URLs:
{url_hints}

{chr(10).join(blocks)}

Return ONLY valid JSON (no markdown):
{{"candidate_name": "...", "certificate_id": "...", "issuer_name": "...", "issuer_url": "...", "certificate_date": "..."}}
"""

    # --- Cleaning helpers ----------------------------------------------------

    def _clean_certificate_id(self, cert_id: Optional[str]) -> Optional[str]:
        """Clean certificate ID by removing spaces and fixing OCR errors"""
        if not cert_id:
            return cert_id
        cleaned = ''.join(cert_id.split())
        cleaned = cleaned.replace('|', '1').replace('é', '6').replace('ö', 'o').replace('ï', 'i')
        # l / I read for 1, O read for 0 - only between digits, where letters make no sense
        cleaned = re.sub(r'(?<=\d)l(?=\d)', '1', cleaned)
        cleaned = re.sub(r'^l(?=\d)', '1', cleaned)
        cleaned = re.sub(r'(?<=\d)l$', '1', cleaned)
        cleaned = re.sub(r'(?<=\d)I(?=\d)', '1', cleaned)
        cleaned = re.sub(r'O(?=0)', '0', cleaned)
        cleaned = re.sub(r'(?<=0)O', '0', cleaned)
        return cleaned

    def _clean_issuer_url(self, url: Optional[str], cert_id: Optional[str] = None) -> Optional[str]:
        """Clean and expand issuer URL"""
        if not url:
            return url
        url = re.sub(r"\s+", "", url.strip())
        if not re.match(r'^https?://', url, re.I):
            if re.match(r'^[a-z][a-z0-9+.-]*:', url, re.I):
                return None  # javascript:, file:, data: ... are never valid issuer URLs
            url = 'https://' + url
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if 'ude.my' in domain and cert_id:
                url = f'https://www.udemy.com/certificate/{cert_id}'
            elif 'coursera.org' in domain and 'verify' in parsed.path and cert_id and cert_id not in url:
                url = f'https://www.coursera.org/verify/{cert_id}'
        except Exception as e:
            logger.warning(f"URL parsing failed: {e}, using original URL")
        return url

    def _clean_issuer_name(self, issuer_name: Optional[str]) -> Optional[str]:
        """Clean issuer name by removing common phrases"""
        if not issuer_name:
            return issuer_name
        issuer_name = ' '.join(issuer_name.split())
        phrases_to_remove = [
            'issued by', 'via', 'powered by', 'through',
            'authorized by', 'offered through', 'from',
            'in partnership with', 'in collaboration with',
            'certificate by'
        ]
        # Whole-word match only, so names such as "Viacom" or "Wharton Online" survive
        for phrase in phrases_to_remove:
            matches = list(re.finditer(rf'\b{re.escape(phrase)}\b', issuer_name, re.I))
            if matches:
                issuer_name = issuer_name[matches[0].end():].strip()
        return issuer_name.strip()

    def _validate_image_bytes(self, image_bytes: bytes) -> None:
        if not image_bytes:
            raise ValueError("Image bytes are empty")
        if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
            raise ValueError(f"Image size exceeds maximum of {MAX_IMAGE_SIZE_BYTES / (1024*1024):.0f}MB")
        try:
            with Image.open(io.BytesIO(image_bytes)) as image:
                if image.format not in ('JPEG', 'PNG', 'WEBP', 'BMP', 'TIFF', 'MPO'):
                    raise ValueError(f"Unsupported image format: {image.format}")
                image.verify()
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Invalid or corrupted image data: {e}")

    # --- Heuristics (no LLM) -------------------------------------------------

    def _heuristic_issuer(self, ens: EnsembleResult) -> Optional[Issuer]:
        c = ens.consensus
        for url in c.urls():
            issuer = self.registry.find_by_url(url.value)
            if issuer:
                return issuer
        for cand in c.id_candidates()[:3]:
            issuer = self.registry.infer_from_id(cand.value)
            if issuer:
                return issuer
        # Most engines mentioning an issuer's name/alias as a whole word
        best, best_votes = None, 0
        for issuer in self.registry.issuers:
            keys = [k for k in (issuer.name, *issuer.aliases) if len(k) >= 3]
            votes = sum(
                1 for text in c.engine_texts.values()
                if any(re.search(rf"(?<![A-Za-z0-9]){re.escape(k)}(?![A-Za-z0-9])", text, re.I) for k in keys)
            )
            if votes > best_votes or (votes == best_votes and votes and issuer.is_direct and not best.is_direct):
                best, best_votes = issuer, votes
        return best

    def _heuristic_names(self, ens: EnsembleResult) -> List[Tuple[str, int]]:
        """Name candidates from layout cues, ranked by how many engines read them."""
        found: Dict[str, int] = {}
        for text in ens.image_engine_texts.values():
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            for i, line in enumerate(lines):
                cands = []
                m = _NAME_INTRO.search(line)
                if m:
                    cands.append(m.group(1) or (lines[i + 1] if i + 1 < len(lines) else ""))
                    if not m.group(1).strip() and i + 1 < len(lines):
                        cands.append(lines[i + 1])
                if _NAME_OUTRO.match(line) and i > 0:
                    cands.append(lines[i - 1])
                if re.match(r"^date\b", line, re.I) and i > 0:   # Udemy: learner name sits above "Date"
                    cands.append(lines[i - 1])
                for raw in cands:
                    name = _clean_person_name(raw)
                    if name:
                        found[name] = found.get(name, 0) + 1
        ranked = [(n, len(ens.consensus.support_for_name(n))) for n in found]
        return sorted(ranked, key=lambda t: (t[1], found[t[0]]), reverse=True)

    def _heuristic_fields(self, ens: EnsembleResult) -> dict:
        issuer = self._heuristic_issuer(ens)
        names = self._heuristic_names(ens)
        urls = ens.consensus.urls()
        date = re.search(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b",
                         ens.combined_text())
        return {
            "candidate_name": names[0][0] if names else None,
            "certificate_id": None,   # chosen from the consensus in _reconcile
            "issuer_name": issuer.name if issuer else None,
            "issuer_url": next((u.value for u in urls if self.registry.is_trusted(u.value)), None),
            "certificate_date": date.group(0) if date else None,
        }

    # --- Reconciliation ------------------------------------------------------

    def _reconcile(self, data: dict, ens: EnsembleResult, mode: str) -> dict:
        """Check the LLM/heuristic fields against the cross-engine votes and attach an OCR report."""
        c = ens.consensus
        warnings: List[str] = []

        issuer_name = self._clean_issuer_name(data.get("issuer_name") or "") or None
        issuer_url = data.get("issuer_url") or None
        llm_id = self._clean_certificate_id(data.get("certificate_id") or None) or None

        issuer = self.registry.resolve(issuer_url, llm_id, issuer_name)
        id_regex = issuer.id_regex if issuer else None

        # --- Certificate ID: votes beat a single reading ---
        best = c.best_id(issuer.name if issuer else None, id_regex)
        llm_support = c.support_for_id(llm_id)
        chosen, id_source = llm_id, ("llm" if mode == "llm" else "heuristic")
        if best is not None:
            llm_fits = bool(llm_id) and (id_regex is None or bool(id_regex.fullmatch(llm_id)))
            if normalize_id(best.value) == normalize_id(llm_id or ""):
                chosen, id_source = best.value, ("llm+consensus" if mode == "llm" else "consensus")
            elif not llm_fits or best.votes > len(llm_support):
                if llm_id:
                    logger.info(f"ID override: LLM {llm_id!r} ({len(llm_support)} engines) -> "
                                f"consensus {best.value!r} ({best.votes} engines)")
                chosen, id_source = best.value, "consensus"
        id_support = c.support_for_id(chosen)
        if issuer is None and chosen:
            issuer = self.registry.infer_from_id(chosen)

        # --- Candidate name: must actually have been read by an engine ---
        name = (data.get("candidate_name") or "").strip() or None
        name_support = c.support_for_name(name)
        name_source = mode
        if not name_support:
            # Missing, or not actually present in any OCR text: use the layout heuristics instead
            alt = self._heuristic_names(ens) if mode == "llm" else []
            if alt and alt[0][1] > 0:
                logger.info(f"Name override: {name!r} not found in any OCR text -> {alt[0][0]!r}")
                name, name_support, name_source = alt[0][0], c.support_for_name(alt[0][0]), "heuristic"
            elif name:
                warnings.append("The holder's name could not be confirmed in the OCR text.")

        # --- Verification URL: keep it consistent with the chosen ID ---
        if not issuer_url:
            issuer_url = next((u.value for u in c.urls() if self.registry.is_trusted(u.value)), None)
        if issuer_url and chosen and normalize_id(chosen) not in normalize_id(issuer_url):
            tail = issuer_url.rstrip("/").rsplit("/", 1)[-1]
            if len(normalize_id(tail)) >= 6 and "?" not in tail:
                issuer_url = issuer_url.rstrip("/")[: -len(tail)] + chosen
        issuer_url = self._clean_issuer_url(issuer_url, chosen) if issuer_url else None

        # --- Cross-checks ---
        n_sources = c.engine_count
        if chosen and n_sources >= 2 and len(id_support) < 2:
            warnings.append("Only one OCR engine read this certificate ID; double-check it against the document.")
        pdf_text = next((r.text for r in ens.ok_results if r.name == "pdf_text"), None)
        if pdf_text and chosen and id_regex is not None:
            pdf_ids = {normalize_id(m.group(0)) for m in id_regex.finditer(pdf_text)}
            if pdf_ids and normalize_id(chosen) not in pdf_ids:
                warnings.append("The PDF's embedded text shows a different certificate ID than the visible page.")

        engines_used = [r.name for r in ens.ok_results]
        ocr_report = {
            "mode": mode,
            "engines": [r.summary() for r in ens.results],
            "engines_used": engines_used,
            "sources": n_sources,
            "visible_words": max((len(t.split()) for t in ens.image_engine_texts.values()), default=0),
            "qr_codes": ens.qr_codes,
            "certificate_id": {
                "value": chosen, "source": id_source, "votes": len(id_support),
                "engines": sorted(id_support), "agreement": round(len(id_support) / n_sources, 2) if n_sources else 0.0,
            },
            "candidate_name": {
                "value": name, "source": name_source, "votes": len(name_support),
                "engines": sorted(name_support), "agreement": round(len(name_support) / n_sources, 2) if n_sources else 0.0,
            },
            "warnings": warnings,
        }

        full_text = re.sub(r"\s+", " ", (next(iter(ens.image_engine_texts.values()), "") or ens.combined_text()))
        return {
            "candidate_name": name,
            "certificate_id": chosen,
            "issuer_name": issuer.name if issuer else issuer_name,
            "issuer_org": issuer_name,
            "issuer_url": issuer_url,
            "certificate_date": (data.get("certificate_date") or None),
            "raw_text_snippet": full_text[:MAX_TEXT_SNIPPET_LENGTH] + ("..." if len(full_text) > MAX_TEXT_SNIPPET_LENGTH else ""),
            "ocr": ocr_report,
        }

    # --- Entry point ---------------------------------------------------------

    async def run_ocr(self, image_bytes: bytes, pdf_bytes: Optional[bytes] = None) -> EnsembleResult:
        self._validate_image_bytes(image_bytes)
        ens = await self.ensemble.run(image_bytes, pdf_bytes)
        if not ens.image_engine_texts:
            errors = "; ".join(f"{r.name}: {r.error}" for r in ens.results if r.error)
            raise ValueError(f"No text could be read from the certificate ({errors or 'all OCR engines failed'}).")
        return ens

    async def extract(self, image_bytes: bytes, pdf_bytes: Optional[bytes] = None,
                      ens: Optional[EnsembleResult] = None) -> dict:
        """Extract certificate fields. `pdf_bytes` enables the PDF text-layer engine."""
        if ens is None:
            ens = await self.run_ocr(image_bytes, pdf_bytes)

        mode = "heuristic"
        data: dict = {}
        if self.llm_available:
            try:
                data = await self._call_llm(self._build_prompt(ens))
                mode = "llm"
            except Exception as e:
                logger.warning(f"LLM extraction failed ({e}); falling back to OCR heuristics")
        if mode == "heuristic":
            data = self._heuristic_fields(ens)

        result = self._reconcile(data, ens, mode)
        logger.info(f"Extraction ({mode}): name={result['candidate_name']!r} issuer={result['issuer_name']!r} "
                    f"id={result['certificate_id']!r} id_votes={result['ocr']['certificate_id']['votes']}/"
                    f"{result['ocr']['sources']}")
        return result
