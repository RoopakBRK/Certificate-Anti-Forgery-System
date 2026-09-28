"""
app/reports.py
Stateless signed verification reports.

A report token is base64url(JSON payload) + "." + base64url(HMAC-SHA256). It can only be
created by this server, so the public validation page can trust what it decodes
(nobody can hand-craft a "verified" certificate URL).
"""
import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Optional

from app.config import config

logger = logging.getLogger(__name__)

if config.REPORT_SECRET:
    _SECRET = config.REPORT_SECRET.encode()
else:
    # Tokens issued with an ephemeral key stop validating after a restart
    _SECRET = secrets.token_bytes(32)
    logger.warning("REPORT_SECRET is not set: using an ephemeral key; reports will not survive a restart.")


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(body: str) -> str:
    return _b64e(hmac.new(_SECRET, body.encode(), hashlib.sha256).digest())


def issue_report(payload: dict) -> str:
    data = dict(payload)
    data.setdefault("verified_at", int(time.time()))
    body = _b64e(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode())
    return f"{body}.{_sign(body)}"


def read_report(token: str) -> Optional[dict]:
    """Return the payload if the signature is valid, else None."""
    try:
        body, signature = token.split(".", 1)
        if not hmac.compare_digest(signature, _sign(body)):
            return None
        payload = json.loads(_b64d(body))
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None
