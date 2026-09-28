"""
app/security.py
Request guards: optional API-key auth and a simple per-client sliding-window rate limit.
"""
import hmac
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import Header, HTTPException, Request

from app.config import config

_hits = defaultdict(deque)


async def require_access(request: Request, x_api_key: Optional[str] = Header(default=None)):
    """Dependency for expensive endpoints."""
    if config.API_KEYS:
        if not x_api_key or not any(hmac.compare_digest(x_api_key, k) for k in config.API_KEYS):
            raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    limit = config.RATE_LIMIT_PER_MINUTE
    if limit <= 0:
        return
    client = x_api_key or (request.client.host if request.client else "unknown")
    now = time.monotonic()
    window = _hits[client]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= limit:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")
    window.append(now)
