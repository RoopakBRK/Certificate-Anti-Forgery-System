"""
app/agents/ocr/vlm.py
Vision-language reader: one cloud model looks at the page image itself and returns the fields.

The ensemble starts it together with the OCR engines and never waits for it. The extraction
agent uses the answer only if it has already arrived at a point the pipeline reaches anyway,
so a slow or failing model costs no time. Opt-in via VLM_PROVIDER, because the page image
leaves the server.
"""
import asyncio
import base64
import io
import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx
from PIL import Image

from app.config import config
from .engines import _downscale

logger = logging.getLogger(__name__)

VLM_ENGINE = "vlm"          # the vision model's name in the OCR report
MAX_SIDE = 1600             # long side sent to the model: small ID text stays legible, the upload stays small
MAX_OUTPUT_TOKENS = 400     # five short fields; a short answer is a fast answer

# OpenAI-compatible chat endpoints that accept an image
_ENDPOINTS = {
    "mistral": "https://api.mistral.ai/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "huggingface": "https://router.huggingface.co/v1/chat/completions",
}
# huggingface has no default: set VLM_MODEL to a vision-capable model
_DEFAULT_MODELS = {"mistral": "ministral-8b-latest", "groq": "qwen/qwen3.8-27b"}
_JSON_MODE = {"mistral", "groq"}


@dataclass
class VLMReading:
    ok: bool
    text: str = ""              # the model's raw answer (JSON); the extraction agent parses it
    seconds: float = 0.0
    error: Optional[str] = None


def _to_data_uri(img: Image.Image) -> str:
    buf = io.BytesIO()
    _downscale(img, MAX_SIDE).save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


class VLMReader:
    def __init__(self, prompt: str, provider: Optional[str] = None, model: Optional[str] = None,
                 api_key: Optional[str] = None, transport: Optional[httpx.AsyncBaseTransport] = None):
        self.prompt = prompt
        self.provider = config.VLM_PROVIDER if provider is None else provider
        self.model = model or config.VLM_MODEL or _DEFAULT_MODELS.get(self.provider, "")
        self.api_key = config.provider_api_key(self.provider) if api_key is None else api_key
        self._transport = transport

    def available(self) -> bool:
        return bool(self.provider in _ENDPOINTS and self.model and self.api_key)

    async def read(self, img: Image.Image) -> VLMReading:
        """One request, no retries (a retry would arrive too late to be used). Never raises."""
        start = time.time()
        try:
            async with asyncio.timeout(config.VLM_TIMEOUT):
                data_uri = await asyncio.to_thread(_to_data_uri, img)
                body = {
                    "model": self.model,
                    "temperature": 0,
                    "max_tokens": MAX_OUTPUT_TOKENS,
                    "messages": [{"role": "user", "content": [
                        {"type": "text", "text": self.prompt},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ]}],
                }
                if self.provider in _JSON_MODE:
                    body["response_format"] = {"type": "json_object"}
                async with httpx.AsyncClient(timeout=config.VLM_TIMEOUT, transport=self._transport) as client:
                    resp = await client.post(_ENDPOINTS[self.provider], json=body,
                                             headers={"Authorization": f"Bearer {self.api_key}"})
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            text = (resp.json()["choices"][0]["message"]["content"] or "").strip()
            return VLMReading(ok=bool(text), text=text, seconds=time.time() - start,
                              error=None if text else "empty answer")
        except Exception as e:
            error = (str(e) or type(e).__name__)[:200]
            logger.warning(f"Vision model {self.model} failed: {error}")
            return VLMReading(ok=False, seconds=time.time() - start, error=error)
