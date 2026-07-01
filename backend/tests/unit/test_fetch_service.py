import httpx
import pytest

from src.services import fetch_service
from src.services.fetch_service import (
    FetchError,
    discover_links,
    looks_like_js_shell,
    same_host,
    validate_url,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://10.1.2.3/",
        "http://192.168.0.1/",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata (SSRF classic)
        "http://100.64.0.1/",  # RFC 6598 CGNAT / shared space (not is_global)
        "http://[::1]/",
        "ftp://8.8.8.8/",  # non-http scheme
        "https://",  # no host
        "file:///etc/passwd",
    ],
)
def test_validate_url_rejects_unsafe(url):
    with pytest.raises(FetchError):
        validate_url(url)


async def test_pinned_transport_rejects_non_public_ip():
    # The connect-time guard is the authoritative SSRF check (defeats DNS rebinding): an
    # internal address is refused before any connection, even though validate_url ran earlier.
    transport = fetch_service._PinnedTransport()
    request = httpx.Request("GET", "http://10.0.0.1/")
    with pytest.raises(FetchError):
        await transport.handle_async_request(request)


async def test_sitemap_index_recurses_to_page_urls(monkeypatch):
    index_xml = (
        '<?xml version="1.0"?><sitemapindex>'
        "<sitemap><loc>https://x.example/sitemap-listings.xml</loc></sitemap>"
        "</sitemapindex>"
    )
    child_xml = (
        '<?xml version="1.0"?><urlset>'
        "<url><loc>https://x.example/listing/1</loc></url>"
        "<url><loc>https://x.example/listing/2</loc></url>"
        "</urlset>"
    )

    async def fake_fetch_html(url, client=None):
        if url.endswith("/sitemap.xml"):
            return index_xml
        if url.endswith("sitemap-listings.xml"):
            return child_xml
        raise FetchError("unexpected url")

    monkeypatch.setattr(fetch_service, "fetch_html", fake_fetch_html)
    urls = await fetch_service._sitemap_urls("https://x.example/home", None)
    # The .xml child sitemap is expanded, not returned; only real page URLs come back.
    assert urls == [
        "https://x.example/listing/1",
        "https://x.example/listing/2",
    ]


@pytest.mark.parametrize("url", ["http://8.8.8.8/", "https://1.1.1.1/path"])
def test_validate_url_allows_public_ip(url):
    # IP literals avoid a real DNS lookup in the test.
    assert validate_url(url) == url


def test_same_host():
    assert same_host("https://a.com/x", "https://a.com/y")
    assert not same_host("https://a.com/x", "https://b.com/y")


def test_discover_links_same_host_only_and_absolutised():
    html = """
    <a href="/listings/1">one</a>
    <a href="listings/2#gallery">two</a>
    <a href="https://other.com/x">off-site</a>
    <a href="mailto:me@x.com">mail</a>
    <a href="tel:+1519">call</a>
    <a href="#top">anchor</a>
    """
    links = discover_links("https://realtor.example/home", html)
    assert links == [
        "https://realtor.example/listings/1",
        "https://realtor.example/listings/2",
    ]


def test_looks_like_js_shell():
    assert looks_like_js_shell("<html><body><div id='root'></div></body></html>")
    assert not looks_like_js_shell(
        '<html><head><script type="application/ld+json">{}</script></head>'
        "<body></body></html>"
    )
    assert not looks_like_js_shell("<html><body>" + "home " * 200 + "</body></html>")
