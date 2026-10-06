import asyncio

from app.schemas import ExtractionResult
from app.agents.verification import service as svc


PAGE = "Certificate of Completion. This certifies that Jane Doe completed the course. " * 10


def _extraction(**kw):
    base = dict(candidate_name="Jane Doe", certificate_id="ABCD1234EFGH", issuer_name="Coursera")
    base.update(kw)
    return ExtractionResult(**base)


def _service(monkeypatch, page_text, screenshot=None):
    async def fake_fetch(url, use_browser=True, force_browser=False):
        return page_text, screenshot
    monkeypatch.setattr(svc, "fetch_page_text", fake_fetch)
    return svc.VerificationService()


def test_verified_when_name_and_id_present(monkeypatch):
    s = _service(monkeypatch, PAGE)
    r = asyncio.run(s.verify(_extraction()))
    assert r.is_verified and r.trusted_domain


def test_wrong_name_fails(monkeypatch):
    s = _service(monkeypatch, PAGE)
    r = asyncio.run(s.verify(_extraction(candidate_name="Mallory Evil")))
    assert not r.is_verified


def test_missing_id_fails(monkeypatch):
    s = _service(monkeypatch, PAGE)
    r = asyncio.run(s.verify(_extraction(certificate_id=None)))
    assert not r.is_verified and r.method == "validation_error"


def test_untrusted_issuer_url_not_fetched(monkeypatch):
    calls = []

    async def fake_fetch(url, **kw):
        calls.append(url)
        return PAGE, None
    monkeypatch.setattr(svc, "fetch_page_text", fake_fetch)
    s = svc.VerificationService()
    r = asyncio.run(s.verify(_extraction(issuer_name=None, issuer_org=None, issuer_url="https://evil.example.com/x")))
    assert not r.is_verified and r.method == "security_check"
    assert calls == []


def test_manual_rejects_untrusted_and_short_id(monkeypatch):
    s = _service(monkeypatch, "ABCD1234EFGH " * 100)
    r = asyncio.run(s.manual_verify("ABCD1234EFGH", "https://evil.example.com/x"))
    assert not r.is_verified and not r.trusted_domain
    r = asyncio.run(s.manual_verify("123", "https://www.coursera.org/verify/123"))
    assert not r.is_verified


def test_manual_verified_on_trusted_page(monkeypatch):
    s = _service(monkeypatch, "Certificate id ABCD-1234-EFGH issued " * 20)
    r = asyncio.run(s.manual_verify("ABCD1234EFGH", "https://www.coursera.org/verify/ABCD1234EFGH"))
    assert r.is_verified


def test_issuer_bot_wall_is_reported_not_scored(monkeypatch):
    wall = ("www.udemy.com Performing security verification This website uses a security service "
            "to protect against malicious bots. This page is displayed while the website verifies you are not a bot.")
    s = _service(monkeypatch, wall)
    r = asyncio.run(s.verify(_extraction()))
    assert not r.is_verified and r.method == "issuer_blocked"
