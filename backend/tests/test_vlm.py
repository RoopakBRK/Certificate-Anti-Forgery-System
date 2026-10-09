"""
The vision model is a helper that must never cost time: these tests pin down when its
answer is used, when it is dropped, and that the OCR votes still decide.
"""
import asyncio
import io
import json
import time

import httpx
import pytest
from PIL import Image

from app.agents.ext import ExtractionAgent
from app.agents.ocr import ensemble as ensemble_module
from app.agents.ocr.consensus import Consensus
from app.agents.ocr.engines import EngineResult, OCREngine
from app.agents.ocr.ensemble import EnsembleResult, OCREnsemble
from app.agents.ocr.vlm import VLMReader, VLMReading
from app.agents.verification.sources import _is_distinctive, default_registry
from app.schemas import ExtractionResult

UDEMY_ID = "UC-3f2a9c41-7b6e-4d1a-9c0f-5e8b2a7d6c13"
MISREAD_ID = "UC-3f2a9c41-7b6e-4d1a-9c0f-5e8b2a7d6c18"   # last character wrong
UDEMY_PAGE = f"""Udemy
Certificate no: {UDEMY_ID}
Certificate url: ude.my/{UDEMY_ID}
Reference Number: 0004
CERTIFICATE OF COMPLETION
Instructors
Alan Placeholder
Maya Fictional
Date
March 14, 2023"""
UDEMY_TEXTS = {"tesseract": UDEMY_PAGE, "paddle": UDEMY_PAGE, "easyocr": UDEMY_PAGE}
GOOD = {"candidate_name": "Maya Fictional", "certificate_id": UDEMY_ID, "issuer_name": "Udemy",
        "issuer_url": f"ude.my/{UDEMY_ID}", "certificate_date": "March 14, 2023"}
# The text LLM mistakes the instructor for the learner (it cannot see the layout)
LLM_WRONG_NAME = {**GOOD, "candidate_name": "Alan Placeholder"}

SLOW = 30.0   # a vision model that would visibly stall the request if anything waited for it


def _ensemble(texts, vlm_task=None):
    patterns = default_registry().id_patterns()
    consensus = Consensus(texts, patterns, {n for n, rx in patterns if _is_distinctive(rx)})
    results = [EngineResult(name, ok=True, text=t) for name, t in texts.items()]
    return EnsembleResult(image=None, results=results, consensus=consensus, vlm_task=vlm_task)


async def _reading(fields=None, delay=0.0, reading=None):
    await asyncio.sleep(delay)
    return reading or VLMReading(ok=True, text=json.dumps(fields), seconds=delay)


def _agent(llm_answer=None, llm_delay=0.0, api_key="key"):
    """An agent whose text LLM is faked; agent.llm_calls counts how often it was asked."""
    agent = ExtractionAgent(api_key=api_key, ensemble=object())
    agent.llm_calls = 0

    async def fake_llm(_prompt):
        agent.llm_calls += 1
        await asyncio.sleep(llm_delay)
        return dict(llm_answer)
    agent._call_llm = fake_llm
    return agent


def _run(agent, texts, vlm_ready=False, **reading_kwargs):
    """Extract with a vision reading in flight; vlm_ready means it arrived before OCR finished."""
    async def go():
        task = asyncio.create_task(_reading(**reading_kwargs))
        if vlm_ready:
            await task
        start = time.perf_counter()
        out = await agent.extract(b"", ens=_ensemble(texts, task))
        elapsed = time.perf_counter() - start
        await asyncio.sleep(0)   # let a cancellation land
        return out, elapsed, task
    return asyncio.run(go())


def _vlm_entry(out):
    return next(e for e in out["ocr"]["engines"] if e["name"] == "vlm")


# --- Latency ------------------------------------------------------------------

def test_confirmed_vision_reading_replaces_the_llm_call():
    agent = _agent(llm_answer=LLM_WRONG_NAME)
    out, _, _ = _run(agent, UDEMY_TEXTS, vlm_ready=True, fields=GOOD)
    assert agent.llm_calls == 0                       # one model call fewer than without a vision model
    assert out["ocr"]["mode"] == "vlm"
    assert out["candidate_name"] == "Maya Fictional" and out["certificate_id"] == UDEMY_ID
    assert out["ocr"]["certificate_id"]["source"] == "vlm+consensus"
    assert out["ocr"]["sources"] == 4 and out["ocr"]["certificate_id"]["votes"] == 4
    assert "vlm" in out["ocr"]["engines_used"]
    report = ExtractionResult(**out).ocr              # the API schema accepts the vision model's entry
    assert report.mode == "vlm" and report.engines[-1].name == "vlm" and report.engines[-1].ok


def test_slow_vision_model_is_never_waited_for():
    agent = _agent(llm_answer=GOOD, llm_delay=0.05)
    out, elapsed, task = _run(agent, UDEMY_TEXTS, fields=GOOD, delay=SLOW)
    assert elapsed < 1.0                              # the LLM's 0.05s, not the vision model's 30s
    assert task.cancelled()                           # and its request is stopped, not left running
    assert out["ocr"]["mode"] == "llm" and out["certificate_id"] == UDEMY_ID
    assert _vlm_entry(out) == {"name": "vlm", "ok": False, "chars": 0, "seconds": 0.0,
                               "confidence": None, "error": "not ready in time"}
    assert out["ocr"]["sources"] == 3 and "vlm" not in out["ocr"]["engines_used"]


def test_slow_vision_model_is_not_waited_for_without_an_llm_either():
    agent = _agent(api_key="")
    out, elapsed, task = _run(agent, UDEMY_TEXTS, fields=GOOD, delay=SLOW)
    assert elapsed < 1.0 and task.cancelled()
    assert out["ocr"]["mode"] == "heuristic" and out["certificate_id"] == UDEMY_ID


def test_reading_that_arrives_during_the_llm_call_is_merged():
    agent = _agent(llm_answer=LLM_WRONG_NAME, llm_delay=0.3)
    out, elapsed, _ = _run(agent, UDEMY_TEXTS, fields={**GOOD, "certificate_id": MISREAD_ID}, delay=0.05)
    assert agent.llm_calls == 1 and elapsed < 1.0
    assert out["ocr"]["mode"] == "vlm+llm"
    # the vision model sees who the learner is ...
    assert out["candidate_name"] == "Maya Fictional"
    assert out["ocr"]["candidate_name"]["source"] == "vlm"
    # ... but its misread ID loses to the one the OCR engines agree on
    assert out["certificate_id"] == UDEMY_ID
    assert out["ocr"]["certificate_id"]["source"] == "llm+consensus"
    assert "vlm" not in out["ocr"]["certificate_id"]["engines"]


# --- The OCR votes still decide -------------------------------------------------

def test_reading_the_ocr_text_does_not_confirm_still_goes_to_the_llm():
    agent = _agent(llm_answer=GOOD)
    out, _, _ = _run(agent, UDEMY_TEXTS, vlm_ready=True, fields={**GOOD, "certificate_id": MISREAD_ID})
    assert agent.llm_calls == 1
    assert out["certificate_id"] == UDEMY_ID and UDEMY_ID in out["issuer_url"]


def test_misread_id_from_the_vision_model_alone_loses_to_the_ocr_votes():
    agent = _agent(api_key="")
    out, _, _ = _run(agent, UDEMY_TEXTS, vlm_ready=True, fields={**GOOD, "certificate_id": MISREAD_ID})
    assert out["ocr"]["mode"] == "vlm"
    assert out["certificate_id"] == UDEMY_ID
    assert out["ocr"]["certificate_id"]["source"] == "consensus"
    assert out["ocr"]["certificate_id"]["votes"] == 3   # the vision model does not count: it read something else


@pytest.mark.parametrize("api_key", ["key", ""])
def test_ocr_agreement_overrules_a_name_only_the_vision_model_read(api_key):
    """A vision model that 'corrects' an unusual name must not beat three engines that read it."""
    agent = _agent(llm_answer=GOOD, api_key=api_key)
    out, _, _ = _run(agent, UDEMY_TEXTS, vlm_ready=True, fields={**GOOD, "candidate_name": "Maria Fictional"})
    assert out["candidate_name"] == "Maya Fictional"
    assert out["ocr"]["candidate_name"]["source"] == ("llm" if api_key else "heuristic")
    assert out["ocr"]["candidate_name"]["votes"] == 3


def test_script_font_name_only_the_vision_model_can_read_is_kept_with_a_warning():
    # Each OCR engine garbles the script-font name differently; neither reading matches the other
    texts = {
        "tesseract": "coursera\nJobias Nonesuch\nhas successfully completed\nVerify at:\nhttps://coursera.org/verify/QX7M2KD9TLPA",
        "paddle": "coursera\nTobras Nanesuch\nhas successfully completed\nVerify at:\nhttps://coursera.org/verify/QX7M2KD9TLPA",
    }
    seen = {"candidate_name": "Tobias Nonesuch", "certificate_id": "QX7M2KD9TLPA", "issuer_name": "Coursera",
            "issuer_url": "https://coursera.org/verify/QX7M2KD9TLPA", "certificate_date": ""}
    agent = _agent(llm_answer={**seen, "candidate_name": "Jobias Nonesuch"})
    out, _, _ = _run(agent, texts, vlm_ready=True, fields=seen)
    assert out["candidate_name"] == "Tobias Nonesuch"
    assert out["ocr"]["candidate_name"]["source"] == "vlm"
    assert out["ocr"]["candidate_name"]["engines"] == ["vlm"]
    assert "Only the vision model read the holder's name; no OCR engine confirmed it." in out["ocr"]["warnings"]
    assert out["certificate_id"] == "QX7M2KD9TLPA" and out["ocr"]["certificate_id"]["votes"] == 3


# --- Failures cost nothing ------------------------------------------------------

@pytest.mark.parametrize("reading,error", [
    (VLMReading(ok=False, seconds=0.4, error="HTTP 429: rate limited"), "HTTP 429: rate limited"),
    (VLMReading(ok=True, text="I cannot read this image.", seconds=0.4), "unreadable answer"),
])
def test_failed_vision_reading_leaves_the_llm_path_unchanged(reading, error):
    agent = _agent(llm_answer=GOOD)
    out, _, _ = _run(agent, UDEMY_TEXTS, vlm_ready=True, reading=reading)
    assert agent.llm_calls == 1 and out["ocr"]["mode"] == "llm"
    assert out["candidate_name"] == "Maya Fictional" and out["certificate_id"] == UDEMY_ID
    assert _vlm_entry(out)["ok"] is False and _vlm_entry(out)["error"] == error
    assert out["ocr"]["sources"] == 3


def test_non_string_fields_from_a_model_are_tolerated():
    agent = _agent(llm_answer=GOOD)
    out, _, _ = _run(agent, UDEMY_TEXTS, vlm_ready=True,
                     fields={"candidate_name": None, "certificate_id": 12345678, "issuer_name": ["Udemy"]})
    assert out["candidate_name"] == "Maya Fictional" and out["certificate_id"] == UDEMY_ID


# --- The reader and the ensemble ------------------------------------------------

def _reader(handler, **kwargs):
    kwargs = {"provider": "mistral", "model": "vision-model", "api_key": "secret", **kwargs}
    return VLMReader("copy the fields", transport=httpx.MockTransport(handler), **kwargs)


def test_reader_sends_the_page_image_and_returns_the_raw_answer():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"], seen["auth"], seen["body"] = str(request.url), request.headers["authorization"], json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(GOOD)}}]})

    reading = asyncio.run(_reader(handler).read(Image.new("RGB", (3200, 1600), "white")))
    assert reading.ok and json.loads(reading.text) == GOOD
    assert seen["url"] == "https://api.mistral.ai/v1/chat/completions" and seen["auth"] == "Bearer secret"
    text_part, image_part = seen["body"]["messages"][0]["content"]
    assert text_part == {"type": "text", "text": "copy the fields"}
    assert image_part["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert seen["body"]["model"] == "vision-model" and seen["body"]["response_format"] == {"type": "json_object"}


def test_reader_reports_failures_instead_of_raising():
    def rate_limited(_request):
        return httpx.Response(429, json={"message": "Rate limit exceeded"})

    def unreachable(_request):
        raise httpx.ConnectError("network down")

    image = Image.new("RGB", (200, 100), "white")
    for handler, expected in ((rate_limited, "HTTP 429"), (unreachable, "network down")):
        reading = asyncio.run(_reader(handler).read(image))
        assert not reading.ok and expected in reading.error


def test_reader_is_off_unless_provider_key_and_model_are_all_set():
    assert not VLMReader("p").available()                                             # VLM_PROVIDER unset
    assert not VLMReader("p", provider="mistral", api_key="").available()
    assert not VLMReader("p", provider="huggingface", api_key="k").available()        # no default model
    assert not VLMReader("p", provider="elsewhere", model="m", api_key="k").available()
    assert VLMReader("p", provider="mistral", api_key="k").available()
    assert VLMReader("p", provider="huggingface", model="m", api_key="k").available()


def test_ensemble_starts_the_vision_model_but_returns_without_it(monkeypatch):
    class FakeEngine(OCREngine):
        name = "fake"

        def _recognise(self, img, pdf_bytes=None):
            return UDEMY_PAGE.splitlines(), None

    class SlowVLM:
        async def read(self, _img):
            return await _reading(fields=GOOD, delay=SLOW)

    monkeypatch.setitem(ensemble_module.ENGINE_CLASSES, "fake", FakeEngine)
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), "white").save(buf, format="PNG")

    async def go():
        ens = await OCREnsemble(engine_names=["fake"], vlm=SlowVLM()).run(buf.getvalue())
        started, finished = ens.vlm_task is not None, ens.vlm_task.done()
        ens.vlm_task.cancel()
        return ens, started, finished

    start = time.perf_counter()
    ens, started, finished = asyncio.run(go())
    assert started and not finished
    assert time.perf_counter() - start < SLOW / 2
    assert ens.consensus.best_id().value == UDEMY_ID
