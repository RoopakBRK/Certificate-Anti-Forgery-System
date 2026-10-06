import asyncio

import pytest

from app.agents.ext import ExtractionAgent, _clean_person_name
from app.agents.ocr.consensus import Consensus
from app.agents.ocr.engines import EngineResult
from app.agents.ocr.ensemble import EnsembleResult
from app.agents.verification.sources import _is_distinctive, default_registry

UDEMY_ID = "UC-baef2223-a25b-4a6d-a92e-1e9fad47af7b"

# Real engine output for the same Udemy certificate: tesseract misreads the ID
TESSERACT = f"""Certificate no: UC-baef2293-a25b-4a6d-a92e-le9fad47af/b
Certificate url: ude.my/UC-baef2223-a25b-4a6d-a92e-le9fad47af7b
Reference Number: 0004
CERTIFICATE OF COMPLETION
C Programming Bootcamp
Instructors Vlad Budnitski
Roopak Krishna
Date March 14, 2023"""
PADDLE = f"""Udemy
Certificate no: {UDEMY_ID}
Certificate url: ude.my/{UDEMY_ID}
Reference Number: O004
CERTIFICATE OF COMPLETION
Instructors
Vlad Budnitski
Roopak Krishna
Date
March 14, 2023"""
EASYOCR = PADDLE.replace("ude.my/", "ude my/")


def _consensus(texts):
    reg = default_registry()
    patterns = reg.id_patterns()
    return Consensus(texts, patterns, {n for n, rx in patterns if _is_distinctive(rx)})


def test_votes_outweigh_single_engine_misread():
    c = _consensus({"tesseract": TESSERACT, "paddle": PADDLE, "easyocr": EASYOCR})
    udemy = default_registry().find("Udemy")
    best = c.best_id(udemy.name, udemy.id_regex)
    assert best.value == UDEMY_ID
    assert best.engines == {"tesseract", "paddle", "easyocr"}   # tesseract's copy repaired l->1, /->7


def test_reference_number_is_never_an_id():
    c = _consensus({"paddle": PADDLE})
    assert all("0004" != x.value for x in c.id_candidates())


def test_coursera_url_and_id():
    text = "ROOPAK BHUKYA\nhas successfully completed\nVerify at:\nhttps://coursera.org/verify/ALS76DHQNMVZ"
    garbled = "Verify at: https Lcoursera org/verifylALSZ6DHQNMVZ"
    c = _consensus({"tesseract": text, "paddle": text, "easyocr": garbled})
    coursera = default_registry().find("Coursera")
    assert c.best_id(coursera.name, coursera.id_regex).value == "ALS76DHQNMVZ"
    assert c.urls()[0].value == "https://coursera.org/verify/ALS76DHQNMVZ"
    assert c.support_for_name("Roopak Bhukya") == {"tesseract", "paddle"}   # not in the garbled text


def test_words_are_not_id_candidates():
    c = _consensus({"a": "CERTIFICATE OF COMPLETION SPECIALIZATION", "b": "CERTIFICATE OF COMPLETION"})
    assert c.id_candidates() == []


@pytest.mark.parametrize("raw,expected", [
    ("Roopak Krishna", "Roopak Krishna"),
    ("ROOPAK BHUKYA", "Roopak Bhukya"),
    ("Certificate of Completion", None),
    ("Instructors Vlad Budnitski", None),
    ("Madonna", None),
])
def test_person_name_cleaning(raw, expected):
    assert _clean_person_name(raw) == expected


def _ensemble(texts):
    results = [EngineResult(name, ok=True, text=t) for name, t in texts.items()]
    return EnsembleResult(image=None, results=results, consensus=_consensus(texts))


def test_heuristic_extraction_without_llm():
    agent = ExtractionAgent(api_key="", ensemble=object())
    ens = _ensemble({"tesseract": TESSERACT, "paddle": PADDLE, "easyocr": EASYOCR})
    out = asyncio.run(agent.extract(b"", ens=ens))
    assert out["ocr"]["mode"] == "heuristic"
    assert out["candidate_name"] == "Roopak Krishna"
    assert out["certificate_id"] == UDEMY_ID
    assert out["issuer_name"] == "Udemy"
    assert out["issuer_url"] == f"https://www.udemy.com/certificate/{UDEMY_ID}"
    assert out["ocr"]["certificate_id"]["votes"] == 3


def test_llm_id_overridden_by_consensus_and_hallucinated_name_rejected(monkeypatch):
    agent = ExtractionAgent(api_key="key", ensemble=object())

    async def fake_llm(_prompt):
        return {"candidate_name": "Vlad Budnitski Jr", "certificate_id": "UC-baef2293-a25b-4a6d-a92e-1e9fad47af7b",
                "issuer_name": "Udemy", "issuer_url": "ude.my/UC-baef2293-a25b-4a6d-a92e-1e9fad47af7b"}
    monkeypatch.setattr(agent, "_call_llm", fake_llm)
    ens = _ensemble({"tesseract": TESSERACT, "paddle": PADDLE, "easyocr": EASYOCR})
    out = asyncio.run(agent.extract(b"", ens=ens))
    assert out["certificate_id"] == UDEMY_ID
    assert out["ocr"]["certificate_id"]["source"] == "consensus"
    assert UDEMY_ID in out["issuer_url"]
    # "Vlad Budnitski Jr" is not read as a unit by any engine -> heuristic name wins
    assert out["candidate_name"] == "Roopak Krishna"


def test_llm_failure_falls_back_to_heuristics(monkeypatch):
    agent = ExtractionAgent(api_key="key", ensemble=object())

    async def broken(_prompt):
        raise RuntimeError("provider down")
    monkeypatch.setattr(agent, "_call_llm", broken)
    out = asyncio.run(agent.extract(b"", ens=_ensemble({"paddle": PADDLE})))
    assert out["ocr"]["mode"] == "heuristic" and out["certificate_id"] == UDEMY_ID
