"""
app/agents/verification/scanner.py
Handles web fetching using HTTPX and Playwright.
"""
import httpx
import asyncio
import random
import logging
import os
import time
import uuid
import glob
from typing import Optional, Tuple
from urllib.parse import urljoin

from .urlguard import is_safe_public_url
from .matching import looks_blocked

logger = logging.getLogger(__name__)

PROOF_RETENTION_SECONDS = int(os.getenv("PROOF_RETENTION_HOURS", "24")) * 3600
PLAYWRIGHT_TOTAL_TIMEOUT = 60

# One shared Chromium instance, at most 3 concurrent pages, created lazily
_pw = None
_browser = None
_browser_lock = asyncio.Lock()
_page_slots = asyncio.Semaphore(3)


async def _get_browser():
    """Return a live shared browser, (re)launching it if needed."""
    global _pw, _browser
    async with _browser_lock:
        if _browser is None or not _browser.is_connected():
            from playwright.async_api import async_playwright
            if _pw is None:
                _pw = await async_playwright().start()
            _browser = await _pw.chromium.launch(headless=True)
        return _browser


async def close_browser():
    """Call on application shutdown."""
    global _pw, _browser
    try:
        if _browser:
            await _browser.close()
        if _pw:
            await _pw.stop()
    finally:
        _browser = _pw = None


def _cleanup_old_proofs(proof_dir: str) -> None:
    """Screenshots may contain personal data: delete anything past the retention window."""
    cutoff = time.time() - PROOF_RETENTION_SECONDS
    for path in glob.glob(os.path.join(proof_dir, "proof_*.png")):
        try:
            if os.path.getmtime(path) < cutoff:
                os.remove(path)
        except OSError:
            pass


USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
]

async def fetch_page_text(url: str, use_browser: bool = True, force_browser: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """
    Scans a URL.
    Args:
        force_browser: If True, skips the fast HTTPX check and goes straight to Playwright.
    Returns:
        (text_content, screenshot_path)
    """
    if not await is_safe_public_url(url):
        logger.warning(f"Blocked non-public or invalid URL: {url}")
        return None, None

    # 1. Try Fast Fetch (HTTPX) - ONLY if not forced to use browser
    if not force_browser:
        text = await _fetch_httpx(url)
        if text and len(text) > 500 and not looks_blocked(text):
            return text, None
        
    # 2. Try Browser Fetch (Playwright)
    if use_browser or force_browser:
        if not force_browser:
            logger.info(f"HTTPX failed for {url}, trying Playwright...")
        return await _fetch_playwright(url)
    
    return None, None

async def _fetch_httpx(url: str) -> Optional[str]:
    """Helper: Fast HTTP request"""
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }
    try:
        # Redirects are followed manually so every hop is re-validated (SSRF)
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False, headers=headers) as client:
            current = url
            for _ in range(5):
                resp = await client.get(current)
                if resp.is_redirect and resp.headers.get("location"):
                    current = urljoin(current, resp.headers["location"])
                    if not await is_safe_public_url(current):
                        logger.warning(f"Blocked redirect to non-public URL: {current}")
                        return None
                    continue
                if resp.status_code == 200:
                    return resp.text
                return None
    except Exception as e:
        logger.debug(f"httpx fetch failed for {url}: {e}")
    return None

async def _fetch_playwright(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Helper: Full Browser + Screenshot (bounded concurrency, hard overall timeout)"""
    try:
        async with _page_slots:
            return await asyncio.wait_for(_render_page(url), timeout=PLAYWRIGHT_TOTAL_TIMEOUT)
    except asyncio.TimeoutError:
        logger.error(f"Playwright exceeded {PLAYWRIGHT_TOTAL_TIMEOUT}s for {url}")
    except Exception as e:
        logger.error(f"Playwright error: {e}")
    return None, None


async def _render_page(url: str) -> Tuple[Optional[str], Optional[str]]:
    browser = await _get_browser()
    context = await browser.new_context(user_agent=random.choice(USER_AGENTS))
    try:
        page = await context.new_page()

        # Block every sub-request (incl. redirects) that targets a non-public host
        async def _guard(route):
            req_url = route.request.url
            if req_url.startswith(("data:", "blob:", "about:")) or await is_safe_public_url(req_url):
                await route.continue_()
            else:
                await route.abort()
        await page.route("**/*", _guard)

        try:
            # Primary attempt: Wait for network idle (most reliable for content)
            await page.goto(url, timeout=30000, wait_until='networkidle')
        except Exception:
            # Fallback: If network is busy (ads/tracking), just wait for DOM
            logger.warning(f"Networkidle timed out for {url}, falling back to domcontentloaded.")
            try:
                await page.wait_for_load_state('domcontentloaded', timeout=10000)
                # Give it a moment to hydrate/render content if networkidle failed
                await page.wait_for_timeout(5000)
            except Exception:
                logger.warning(f"DOM load also timed out for {url}, proceeding with whatever is rendered.")

        proof_dir = os.path.join(os.getcwd(), "proofs")
        os.makedirs(proof_dir, exist_ok=True)
        await asyncio.to_thread(_cleanup_old_proofs, proof_dir)
        screenshot_path = os.path.join(proof_dir, f"proof_{uuid.uuid4().hex}.png")

        await page.screenshot(path=screenshot_path, full_page=True)
        content = await page.inner_text("body")
        return content, screenshot_path
    finally:
        await context.close()
