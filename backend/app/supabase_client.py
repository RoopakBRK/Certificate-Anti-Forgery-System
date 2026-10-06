"""
app/supabase_client.py
Supabase integration: identify the signed-in user (Google OAuth via Supabase Auth) and
store their verification history in public.cafs_reports.

Reports are written with the service-role key, never with the user's token: users can
read and delete their own rows (RLS) but cannot insert, so a VERIFIED row cannot be forged.
"""
import hashlib
import logging
import time
from typing import Optional

import httpx
from fastapi import Header, HTTPException

from app.config import config

logger = logging.getLogger(__name__)

_USER_CACHE_SECONDS = 60
_user_cache: dict = {}   # sha256(token) -> (expires_at, user)


def auth_configured() -> bool:
    return bool(config.SUPABASE_URL and (config.SUPABASE_PUBLISHABLE_KEY or config.SUPABASE_SERVICE_ROLE_KEY))


def storage_configured() -> bool:
    return bool(config.SUPABASE_URL and config.SUPABASE_SERVICE_ROLE_KEY)


async def _fetch_user(token: str) -> Optional[dict]:
    """Ask Supabase Auth who owns this access token (validates signature and expiry)."""
    key = hashlib.sha256(token.encode()).hexdigest()
    now = time.monotonic()
    cached = _user_cache.get(key)
    if cached and cached[0] > now:
        return cached[1]

    apikey = config.SUPABASE_PUBLISHABLE_KEY or config.SUPABASE_SERVICE_ROLE_KEY
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{config.SUPABASE_URL}/auth/v1/user",
                                headers={"apikey": apikey, "Authorization": f"Bearer {token}"})
    if resp.status_code != 200:
        return None
    user = resp.json()
    if len(_user_cache) > 5000:
        _user_cache.clear()
    _user_cache[key] = (now + _USER_CACHE_SECONDS, user)
    return user


async def optional_user(authorization: Optional[str] = Header(default=None)) -> Optional[dict]:
    """FastAPI dependency: the signed-in Supabase user, or None for anonymous requests.

    A token that is present but invalid is rejected (401) rather than silently ignored,
    so the client knows to refresh its session.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    if not auth_configured():
        return None
    token = authorization.split(" ", 1)[1].strip()
    try:
        user = await _fetch_user(token)
    except httpx.HTTPError as e:
        logger.warning(f"Supabase auth check failed: {e}")
        return None   # auth outage: serve the request anonymously rather than failing it
    if user is None:
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    return user


async def save_report(row: dict) -> Optional[str]:
    """Insert one cafs_reports row; returns its id. Failures are logged, never raised."""
    if not storage_configured():
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{config.SUPABASE_URL}/rest/v1/cafs_reports",
                headers={
                    "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
                    "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                json=row,
            )
        if resp.status_code >= 300:
            logger.error(f"Saving report failed: HTTP {resp.status_code} {resp.text[:300]}")
            return None
        body = resp.json()
        return body[0]["id"] if isinstance(body, list) and body else None
    except Exception as e:
        logger.error(f"Saving report failed: {e}")
        return None
