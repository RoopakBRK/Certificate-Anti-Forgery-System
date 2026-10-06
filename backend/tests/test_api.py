import io

from fastapi.testclient import TestClient
from PIL import Image

from app import main
from app.config import config

client = TestClient(main.app)


def _png(size=(64, 64)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
    return buf.getvalue()


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_rejects_non_image():
    r = client.post("/verify", files={"file": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_content_type_is_not_trusted():
    r = client.post("/verify", files={"file": ("x.png", b"not really a png", "image/png")})
    assert r.status_code == 400


def test_upload_size_limit(monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 1024)
    r = client.post("/verify", files={"file": ("x.png", b"\x89PNG\r\n\x1a\n" + b"0" * 2048, "image/png")})
    assert r.status_code == 413


def test_manual_untrusted_url_rejected():
    r = client.post("/verify/manual", json={"certificate_id": "ABCD1234EFGH", "issuer_url": "http://127.0.0.1:8000/x"})
    assert r.status_code == 200
    v = r.json()["verification"]
    assert v["is_verified"] is False and v["trusted_domain"] is False


def test_manual_validation():
    r = client.post("/verify/manual", json={"certificate_id": "x", "issuer_url": "y"})
    assert r.status_code == 422


def test_forensics_dict_converts_to_schema():
    raw = main.forensics_agent.analyze(_png())
    result = main._to_forensics_result(raw)
    assert 0.0 <= result.manipulation_score <= 1.0
    assert isinstance(result.is_high_risk, bool)


def test_full_pipeline_uses_forensics_object(monkeypatch):
    """Regression: /verify used to 500 because forensics returned a dict."""
    async def fake_extract(_, **kw):
        return {"candidate_name": "Jane Doe", "certificate_id": "ABCD1234EFGH", "issuer_name": "Coursera"}

    async def fake_verify(_):
        from app.schemas import VerificationResult
        return VerificationResult(is_verified=True, trusted_domain=True, method="dom_text_match", message="ok")

    monkeypatch.setattr(main.extraction_agent, "extract", fake_extract)
    monkeypatch.setattr(main.verification_service, "verify", fake_verify)
    r = client.post("/verify", files={"file": ("c.png", _png(), "image/png")})
    assert r.status_code == 200, r.text
    assert r.json()["final_verdict"] == "VERIFIED"


def test_inconclusive_forensics_never_verified(monkeypatch):
    async def fake_extract(_, **kw):
        return {"candidate_name": "Jane Doe", "certificate_id": "ABCD1234EFGH", "issuer_name": "Coursera"}

    async def fake_verify(_):
        from app.schemas import VerificationResult
        return VerificationResult(is_verified=True, trusted_domain=True, method="dom_text_match", message="ok")

    monkeypatch.setattr(main.extraction_agent, "extract", fake_extract)
    monkeypatch.setattr(main.verification_service, "verify", fake_verify)
    monkeypatch.setattr(main.forensics_agent, "analyze", lambda _b: {
        "manipulation_score": 0.5, "is_high_risk": False, "inconclusive": True,
        "status": "Inconclusive", "details": [],
    })
    r = client.post("/verify", files={"file": ("c.png", _png(), "image/png")})
    assert r.json()["final_verdict"] == "UNVERIFIED"


def test_report_token_roundtrip_and_tamper():
    from app.reports import issue_report, read_report
    token = issue_report({"candidate_name": "Jane Doe", "verdict": "VERIFIED"})
    assert read_report(token)["candidate_name"] == "Jane Doe"

    body, sig = token.split(".")
    forged_body = issue_report({"candidate_name": "Mallory", "verdict": "VERIFIED"}).split(".")[0]
    assert read_report(f"{forged_body}.{sig}") is None
    assert read_report("garbage") is None

    assert client.get("/report", params={"token": token}).json()["candidate_name"] == "Jane Doe"
    assert client.get("/report", params={"token": f"{forged_body}.{sig}"}).status_code == 404


def test_verified_response_carries_report_token(monkeypatch):
    async def fake_extract(_, **kw):
        return {"candidate_name": "Jane Doe", "certificate_id": "ABCD1234EFGH", "issuer_name": "Coursera"}

    async def fake_verify(_):
        from app.schemas import VerificationResult
        return VerificationResult(is_verified=True, trusted_domain=True, method="dom_text_match", message="ok")

    monkeypatch.setattr(main.extraction_agent, "extract", fake_extract)
    monkeypatch.setattr(main.verification_service, "verify", fake_verify)
    r = client.post("/verify", files={"file": ("c.png", _png(), "image/png")}).json()
    payload = client.get("/report", params={"token": r["report_token"]}).json()
    assert payload["certificate_id"] == "ABCD1234EFGH" and payload["issuer_name"] == "Coursera"
