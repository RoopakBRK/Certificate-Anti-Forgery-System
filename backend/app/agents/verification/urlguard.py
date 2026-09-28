"""
app/agents/verification/urlguard.py
SSRF protection: only http(s) URLs that resolve exclusively to public IPs may be fetched.
"""
import asyncio
import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _is_public_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False


def _resolve_all(host: str) -> list:
    return [info[4][0] for info in socket.getaddrinfo(host, None)]


async def is_safe_public_url(url: str) -> bool:
    """True if `url` is http(s), has a hostname, and every resolved address is public."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        if parsed.username or parsed.password:
            return False
        host = parsed.hostname
        try:
            # Literal IP in the URL
            return _is_public_ip(str(ipaddress.ip_address(host)))
        except ValueError:
            pass
        addrs = await asyncio.to_thread(_resolve_all, host)
        return bool(addrs) and all(_is_public_ip(a) for a in addrs)
    except Exception as e:
        logger.warning(f"URL safety check failed for {url!r}: {e}")
        return False
