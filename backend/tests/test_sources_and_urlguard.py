import asyncio
import pytest

from app.agents.verification.sources import TrustedSourceRegistry
from app.agents.verification.urlguard import is_safe_public_url


@pytest.fixture(scope="module")
def registry():
    return TrustedSourceRegistry()


def test_trusted_exact_hosts(registry):
    assert registry.is_trusted("https://www.coursera.org/verify/ABC123DEF456")
    assert registry.is_trusted("https://credentials.edx.org/credentials/x")


def test_subdomains_and_http_not_trusted(registry):
    assert not registry.is_trusted("https://evil.linkedin.com/x")
    assert not registry.is_trusted("https://coursera.org.evil.com/verify/x")
    assert not registry.is_trusted("http://www.coursera.org/verify/x")
    assert not registry.is_trusted("https://docs.google.com/x")
    assert not registry.is_trusted("javascript:alert(1)")


def test_generate_urls_udemy(registry):
    urls = registry.generate_urls(None, "UC-1234", "Udemy")
    assert "https://www.udemy.com/certificate/UC-1234" in urls


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/", "http://localhost:8000/", "http://169.254.169.254/latest/meta-data",
    "http://10.0.0.5/", "http://[::1]/", "file:///etc/passwd", "ftp://example.com/",
    "http://user:pw@example.com/",
])
def test_ssrf_blocked(url):
    assert asyncio.run(is_safe_public_url(url)) is False
