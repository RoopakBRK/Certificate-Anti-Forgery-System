"""
app/schemas.py
Pydantic models for data validation and API responses.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union
from enum import Enum
import re

# --- Enums ---
def _issuer_enum() -> Enum:
    """IssuerName is generated from the trusted issuer registry (data/onlinelist.csv)."""
    from app.agents.verification.sources import all_issuers
    members = {}
    for issuer in all_issuers():
        key = re.sub(r"[^a-z0-9]+", "_", issuer.name.lower()).strip("_") or "issuer"
        while key in members:
            key += "_"
        members[key] = issuer.name
    return Enum("IssuerName", members, type=str)


IssuerName = _issuer_enum()


# --- Helper Logic ---
def fuzzy_match_issuer(raw_issuer: str):
    """Map a raw issuer string (name, alias or near-miss spelling) to an IssuerName, else None."""
    if not raw_issuer:
        return None
    from app.agents.verification.sources import default_registry
    issuer = default_registry().find(raw_issuer)
    return IssuerName(issuer.name) if issuer else None

# --- Core Models ---

class ForensicsResult(BaseModel):
    manipulation_score: float
    is_high_risk: bool
    status: str
    inconclusive: bool = False
    details: Optional[List[str]] = []
    # LLM Analysis Fields
    llm_analysis: Optional[str] = None
    llm_risk_score: Optional[float] = None
    llm_confidence: Optional[float] = None
    llm_reasoning: Optional[str] = None

class OCRFieldAgreement(BaseModel):
    value: Optional[str] = None
    source: str = "none"          # llm | vlm | llm+consensus | vlm+consensus | consensus | heuristic
    votes: int = 0                # sources (OCR engines, QR, vision model) that read this value
    engines: List[str] = []
    agreement: float = 0.0        # votes / sources


class OCREngineStatus(BaseModel):
    name: str
    ok: bool
    chars: int = 0
    seconds: float = 0.0
    confidence: Optional[float] = None
    error: Optional[str] = None


class OCRReport(BaseModel):
    mode: str                     # who structured the fields: "vlm", "vlm+llm", "llm" or "heuristic"
    engines: List[OCREngineStatus] = []   # includes the vision model ("vlm") when it is switched on
    engines_used: List[str] = []
    sources: int = 0              # engines (+ QR, + the vision model) that produced a reading
    visible_words: int = 0        # words read from the rendered page by the best engine
    qr_codes: List[str] = []
    certificate_id: OCRFieldAgreement = OCRFieldAgreement()
    candidate_name: OCRFieldAgreement = OCRFieldAgreement()
    warnings: List[str] = []


class ExtractionResult(BaseModel):
    candidate_name: Optional[str] = None
    certificate_id: Optional[str] = None
    
    # Can be the Enum OR None
    issuer_name: Optional[IssuerName] = None

    @field_validator("issuer_name", mode="before")
    def validate_issuer(cls, value):
        """Auto-converts string input to Enum using fuzzy matching"""
        if isinstance(value, IssuerName):
            return value
        if value is None:
            return None
        return fuzzy_match_issuer(str(value))

    issuer_url: Optional[str] = None
    issuer_org: Optional[str] = None
    raw_text_snippet: Optional[str] = None
    certificate_date: Optional[str] = None
    ocr: Optional[OCRReport] = None

class VerificationResult(BaseModel):
    is_verified: bool
    trusted_domain: bool
    confidence_score: float = 0.0      # NEW: 0.0 to 1.0 (How close was the match?)
    verification_url: Optional[str] = None  # NEW: The exact link checked (clickable for user)
    method: str = "none"               # NEW: "exact_match", "fuzzy_match", "domain_only", "failed"
    message: str

class CertificateAnalysisResponse(BaseModel):
    filename: str
    final_verdict: str
    forensics: ForensicsResult
    extraction: ExtractionResult
    verification: VerificationResult
    report_token: Optional[str] = None   # signed proof; only issued for VERIFIED results
    report_id: Optional[str] = None      # cafs_reports row id, when the user is signed in

class ManualVerificationRequest(BaseModel):
    certificate_id: str = Field(min_length=3, max_length=128)
    issuer_url: str = Field(min_length=8, max_length=2048)