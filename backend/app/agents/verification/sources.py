"""
app/agents/verification/sources.py
Registry of trusted certificate issuers, loaded from data/onlinelist.csv.

Each issuer row gives its verification URL patterns ("{id}" is replaced with the
certificate ID), the regex its certificate IDs follow, and whether a certificate can be
checked automatically ("direct") or only through a form on the issuer's site ("lookup").
"""
import csv
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Pattern, Set, Tuple
from urllib.parse import quote, urlparse

from app.config import config

logger = logging.getLogger(__name__)

# Characters allowed to appear un-escaped when an ID is placed into a URL path.
# "/" is needed for username/slug IDs (freeCodeCamp, Kaggle); ".." is rejected separately.
_ID_URL_SAFE = "-_./"


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def _is_distinctive(regex: Optional[Pattern]) -> bool:
    """A literal prefix ("UC-", "NPTEL") or 32+ hex characters: unlikely to match by chance."""
    if regex is None:
        return False
    pattern = regex.pattern
    if re.match(r"[A-Za-z]{2,}", pattern):
        return True
    return any(int(n) >= 32 for n in re.findall(r"\[0-9a-f\]\{(\d+)\}", pattern)) or pattern.count("[0-9a-f]") >= 5


@dataclass(frozen=True)
class Issuer:
    name: str
    category: str
    aliases: Tuple[str, ...]
    website_url: str
    verification_url: str
    url_patterns: Tuple[str, ...]
    id_regex: Optional[Pattern]
    id_example: str
    verification_type: str      # "direct" | "lookup"
    notes: str

    @property
    def is_direct(self) -> bool:
        return self.verification_type == "direct" and bool(self.url_patterns)

    def matches_id(self, cert_id: str) -> bool:
        return bool(self.id_regex and cert_id and self.id_regex.fullmatch(cert_id))

    def build_urls(self, cert_id: str) -> List[str]:
        if not cert_id or ".." in cert_id:
            return []
        safe_id = quote(cert_id.strip().strip("/"), safe=_ID_URL_SAFE)
        return [p.replace("{id}", safe_id) for p in self.url_patterns]

    def hosts(self) -> Set[str]:
        return {h for h in (_host(u) for u in (self.verification_url, *self.url_patterns) if u) if h}


def load_issuers(csv_path: str) -> List[Issuer]:
    issuers: List[Issuer] = []
    with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            row = {(k or "").strip(): (v or "").strip() for k, v in row.items()}
            name = row.get("Organization Name")
            if not name:
                continue
            regex = row.get("ID Regex") or ""
            try:
                compiled = re.compile(regex) if regex else None
            except re.error as e:
                logger.warning(f"Bad ID regex for {name!r}: {e}")
                compiled = None
            verification_url = row.get("Verification URL", "")
            if verification_url and not verification_url.startswith(("http://", "https://")):
                verification_url = "https://" + verification_url
            issuers.append(Issuer(
                name=name,
                category=row.get("Category", ""),
                aliases=tuple(a.strip() for a in row.get("Aliases", "").split("|") if a.strip()),
                website_url=row.get("Website URL", ""),
                verification_url=verification_url,
                url_patterns=tuple(p.strip() for p in row.get("URL Patterns", "").split(" ; ") if p.strip()),
                id_regex=compiled,
                id_example=row.get("ID Example", ""),
                verification_type=(row.get("Verification Type") or "lookup").lower(),
                notes=row.get("Notes", ""),
            ))
    return issuers


@lru_cache(maxsize=4)
def _cached_issuers(csv_path: str) -> Tuple[Issuer, ...]:
    try:
        return tuple(load_issuers(csv_path))
    except Exception as e:
        logger.error(f"Could not load trusted issuer registry {csv_path!r}: {e}")
        return ()


def all_issuers() -> Tuple[Issuer, ...]:
    return _cached_issuers(config.CSV_PATH)


class TrustedSourceRegistry:
    def __init__(self, csv_path: Optional[str] = None):
        self.issuers: Tuple[Issuer, ...] = _cached_issuers(csv_path or config.CSV_PATH)
        self.trusted_domains: Set[str] = set()
        self._by_name: Dict[str, Issuer] = {}
        self._by_host: Dict[str, Issuer] = {}
        for issuer in self.issuers:
            for key in (issuer.name, *issuer.aliases):
                self._by_name.setdefault(_norm_name(key), issuer)
            for host in issuer.hosts():
                self.trusted_domains.add(host)
                # The first issuer listing a host owns it (e.g. Credly before IBM)
                self._by_host.setdefault(host, issuer)

    # --- Lookup -------------------------------------------------------------

    def find(self, org_name: Optional[str]) -> Optional[Issuer]:
        """Issuer by name or alias: exact, then whole-word containment, then fuzzy."""
        key = _norm_name(org_name or "")
        if not key:
            return None
        if key in self._by_name:
            return self._by_name[key]
        # "Google Skillshop Certification" -> "Google Skillshop"; longest alias wins
        padded = f" {key} "
        contained = [(len(k), i) for k, i in self._by_name.items() if len(k) >= 3 and f" {k} " in padded]
        if contained:
            return max(contained, key=lambda t: t[0])[1]
        from rapidfuzz import fuzz, process
        match = process.extractOne(key, list(self._by_name), scorer=fuzz.ratio, score_cutoff=85)
        return self._by_name[match[0]] if match else None

    def find_by_url(self, url: Optional[str]) -> Optional[Issuer]:
        return self._by_host.get(_host(url)) if url else None

    def infer_from_id(self, cert_id: Optional[str]) -> Optional[Issuer]:
        """Issuer whose distinctive ID format uniquely matches (e.g. "UC-<uuid>" is always Udemy).

        Generic formats such as 12 upper-case characters are never used to guess an issuer.
        """
        if not cert_id:
            return None
        matches = [i for i in self.issuers
                   if i.is_direct and _is_distinctive(i.id_regex) and i.matches_id(cert_id)]
        distinct = {i.url_patterns for i in matches}
        return matches[0] if len(distinct) == 1 else None

    def resolve(self, url: Optional[str], cert_id: Optional[str], org_name: Optional[str]) -> Optional[Issuer]:
        return self.find(org_name) or self.find_by_url(url) or self.infer_from_id(cert_id)

    def id_patterns(self) -> List[Tuple[str, Pattern]]:
        """(issuer name, compiled ID regex) for every distinct ID format, for OCR consensus."""
        seen, out = set(), []
        for issuer in self.issuers:
            if issuer.id_regex is not None and issuer.id_regex.pattern not in seen:
                seen.add(issuer.id_regex.pattern)
                out.append((issuer.name, issuer.id_regex))
        return out

    # --- Trust + URL generation --------------------------------------------

    def is_trusted(self, url: str) -> bool:
        """Checks that a URL is https and its host exactly matches a trusted domain.

        Subdomains are NOT implicitly trusted: shared hosts such as linkedin.com or
        google.com serve user-controlled content on subdomains.
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname:
                return False
            return _host(url) in self.trusted_domains
        except Exception:
            return False

    def generate_urls(self, url: Optional[str], cert_id: Optional[str], org_name: Optional[str]) -> List[str]:
        """Candidate verification URLs: the one printed on the certificate first, then issuer patterns."""
        urls = [url] if url else []
        issuer = self.resolve(url, cert_id, org_name)
        if issuer and cert_id and issuer.is_direct:
            urls.extend(issuer.build_urls(cert_id))
        return list(dict.fromkeys(urls))


@lru_cache(maxsize=1)
def default_registry() -> TrustedSourceRegistry:
    return TrustedSourceRegistry()
