import asyncio
import os
import shutil

import pytest
from fastapi import HTTPException

from app import supabase_client
from app.agents.forensics.pdf_structure import analyze_pdf
from app.agents.verification.sources import default_registry
from app.config import config
from app.schemas import ExtractionResult

PDF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pdfcourses")


@pytest.mark.parametrize("raw,expected", [
    ("Coursera", "Coursera"), ("Cursera", "Coursera"), ("HarvardX", "edX"),
    ("Google Career Certificates", "Coursera"), ("NPTEL Online Certification", "NPTEL"),
    ("Great Learning Academy", "Great Learning"), ("Infosys Springboard", "Infosys Springboard"),
    ("Some Random LLC", None),
])
def test_issuer_aliases(raw, expected):
    issuer = ExtractionResult(issuer_name=raw).issuer_name
    assert (issuer.value if issuer else None) == expected


def test_issuer_inferred_only_from_distinctive_ids():
    reg = default_registry()
    assert reg.infer_from_id("UC-9ba43c6a-3983-495c-beb2-329801af4557").name == "Udemy"
    assert reg.infer_from_id("NPTEL25CS110S46360038410384681").name == "NPTEL"
    assert reg.infer_from_id("ABCD1234EFGH") is None          # generic 12-char code
    assert reg.infer_from_id("ee7dd4082ab3496dbd2fd850b9ac5be6") is None   # edX / NVIDIA / Cognitive Class


def test_generated_urls_are_escaped_and_trusted():
    reg = default_registry()
    assert reg.generate_urls(None, "../../admin", "Coursera") == []
    assert reg.generate_urls(None, "a b?c", "Coursera")[0] == "https://www.coursera.org/verify/a%20b%3Fc"
    for issuer in reg.issuers:
        for url in issuer.build_urls("TESTID123"):
            assert reg.is_trusted(url), url


def test_every_direct_issuer_has_patterns():
    for issuer in default_registry().issuers:
        if issuer.verification_type == "direct":
            assert issuer.url_patterns and all("{id}" in p for p in issuer.url_patterns), issuer.name


needs_poppler = pytest.mark.skipif(shutil.which("pdfinfo") is None, reason="poppler not installed")


@needs_poppler
def test_pdf_text_overlay_is_detected():
    with open(os.path.join(PDF_DIR, "fakecft.pdf"), "rb") as fh:
        result = analyze_pdf(fh.read(), visible_words=60)
    assert result["suspicious"] and result["overlay_text"] == "Oct. 27, 2024"


@needs_poppler
@pytest.mark.parametrize("name", ["roopakcftmlsample.pdf", "sampleudemycft.pdf", "samplecourseracft.pdf"])
def test_genuine_pdfs_pass(name):
    with open(os.path.join(PDF_DIR, name), "rb") as fh:
        assert not analyze_pdf(fh.read(), visible_words=60)["suspicious"]


def test_optional_user(monkeypatch):
    monkeypatch.setattr(config, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(config, "SUPABASE_PUBLISHABLE_KEY", "pk")

    async def fake_fetch(token):
        return {"id": "u1"} if token == "good" else None
    monkeypatch.setattr(supabase_client, "_fetch_user", fake_fetch)

    assert asyncio.run(supabase_client.optional_user(None)) is None
    assert asyncio.run(supabase_client.optional_user("Bearer good")) == {"id": "u1"}
    with pytest.raises(HTTPException) as err:
        asyncio.run(supabase_client.optional_user("Bearer bad"))
    assert err.value.status_code == 401
