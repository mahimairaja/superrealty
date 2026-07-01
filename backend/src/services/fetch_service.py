"""Fetch and crawl a realtor's OWN site to seed onboarding (the URL is a seed, not the input).

Given one URL we fetch it (SSRF-guarded httpx), discover more same-host pages (sitemap.xml +
on-page links), and return their content. A page that comes back as a JS shell falls back to
Jina Reader (r.jina.ai) which renders the JS and returns clean markdown. Bounded on purpose:
same host only, a page cap, per-request timeout, and public addresses only.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from selectolax.parser import HTMLParser

_UA = "Mozilla/5.0 (compatible; RealtyRecallBot/1.0; +https://realtyrecall.mahimai.ca)"
_TIMEOUT = 12.0
_READER_TIMEOUT = 25.0
_MAX_BYTES = 3_000_000
_MAX_PAGES = 25
_MAX_SITEMAPS = 5  # child sitemaps to expand from a sitemap index
_MAX_SPA_PAGES = 5  # reader-rendered pages for a client-rendered (JS-shell) seed
_CONCURRENCY = 5
_JS_SHELL_TEXT_MIN = 400
_TEXTUAL = ("html", "xml", "text", "json")


class FetchError(Exception):
    """A URL could not be fetched (bad scheme, non-public address, network, or content type)."""


@dataclass
class CrawledPage:
    url: str
    content: str
    is_markdown: (
        bool  # True when it came from the Jina reader fallback (already cleaned)
    )


def _is_public_host(host: str) -> bool:
    """True only if every resolved address for the host is a public, globally-routable IP
    (SSRF guard: blocks localhost, private/link-local ranges, CGNAT/shared 100.64/10, cloud
    metadata like 169.254.169.254, and other special-use ranges in one predicate).
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if not ip.is_global:
            return False
    return True


def validate_url(url: str) -> str:
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise FetchError("only public http(s) URLs are supported")
    if not _is_public_host(parts.hostname):
        raise FetchError("that URL resolves to a non-public address")
    return url


class _PinnedTransport(httpx.AsyncHTTPTransport):
    """Connect only to the exact IP we vetted, closing the DNS-rebinding / TOCTOU gap.

    validate_url() resolves the host once, but httpx would resolve it again at connect time, so
    an attacker serving a TTL-0 record that alternates public/internal answers could pass the
    check and still connect internally. Here we resolve the host, reject a non-public address,
    then pin the connection to that IP (preserving the original hostname for the Host header and
    TLS SNI), so the address we checked is the address we connect to.
    """

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        host = request.url.host
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            port = request.url.port or (443 if request.url.scheme == "https" else 80)
            try:
                infos = await asyncio.get_running_loop().getaddrinfo(host, port)
            except socket.gaierror as exc:
                raise FetchError(f"could not resolve host: {host}") from exc
            if not infos:
                raise FetchError(f"could not resolve host: {host}") from None
            ip = ipaddress.ip_address(infos[0][4][0])
        if not ip.is_global:
            raise FetchError("that URL resolves to a non-public address")
        if "host" not in request.headers:
            request.headers["host"] = host
        request.extensions = {**request.extensions, "sni_hostname": host}
        request.url = request.url.copy_with(host=str(ip))
        return await super().handle_async_request(request)


def _new_client(*, timeout: float, follow_redirects: bool) -> httpx.AsyncClient:
    """An httpx client that pins every connection to a vetted public IP (SSRF-safe)."""
    return httpx.AsyncClient(
        timeout=timeout,
        headers={"User-Agent": _UA},
        follow_redirects=follow_redirects,
        transport=_PinnedTransport(),
    )


def same_host(a: str, b: str) -> bool:
    return urlparse(a).hostname == urlparse(b).hostname


def looks_like_js_shell(html: str) -> bool:
    """A page worth escalating to the reader fallback: no structured data and almost no text."""
    tree = HTMLParser(html)
    if tree.css_first('script[type="application/ld+json"]'):
        return False
    body = tree.body
    text = body.text(separator=" ", strip=True) if body else ""
    return len(text) < _JS_SHELL_TEXT_MIN


def discover_links(base_url: str, html: str) -> list[str]:
    """Same-host page links found on a page, absolutised and deduped (fragments stripped)."""
    tree = HTMLParser(html)
    out: list[str] = []
    seen: set[str] = set()
    for node in tree.css("a[href]"):
        href = node.attributes.get("href")
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        full = urljoin(base_url, href).split("#", 1)[0]
        if full not in seen and same_host(base_url, full):
            seen.add(full)
            out.append(full)
    return out


async def _read_capped(resp: httpx.Response) -> str:
    """Read a STREAMED response body but stop at _MAX_BYTES, so a huge (or malicious) page can't
    exhaust memory: previously the whole body was buffered before truncating the text. Peak
    memory is bounded to about _MAX_BYTES plus one chunk; the first _MAX_BYTES of text is kept
    (listing structured data lives near the top of the document), so this stays graceful.
    """
    total = 0
    chunks: list[bytes] = []
    async for chunk in resp.aiter_bytes():
        chunks.append(chunk)
        total += len(chunk)
        if total >= _MAX_BYTES:
            break  # stop reading; do not buffer the rest
    encoding = resp.charset_encoding or "utf-8"
    return b"".join(chunks).decode(encoding, errors="replace")[:_MAX_BYTES]


async def _get(client: httpx.AsyncClient, url: str) -> httpx.Response:
    """GET (streamed) with manual redirect handling so every hop is re-validated against the
    SSRF guard. Returns an open streamed response; the caller reads it capped and closes it."""
    current = validate_url(url)
    for _ in range(4):
        resp = await client.send(client.build_request("GET", current), stream=True)
        if resp.is_redirect:
            await resp.aclose()
            location = resp.headers.get("location")
            if not location:
                break
            current = validate_url(urljoin(current, location))
            continue
        return resp
    raise FetchError("too many redirects")


async def fetch_html(url: str, client: httpx.AsyncClient | None = None) -> str:
    owns_client = client is None
    client = client or _new_client(timeout=_TIMEOUT, follow_redirects=False)
    try:
        resp = await _get(client, url)
        try:
            if resp.status_code >= 400:
                raise FetchError(f"HTTP {resp.status_code}")
            ctype = resp.headers.get("content-type", "").lower()
            if not any(t in ctype for t in _TEXTUAL):
                raise FetchError(f"unexpected content type: {ctype or 'unknown'}")
            return await _read_capped(resp)
        finally:
            await resp.aclose()
    except httpx.HTTPError as exc:
        raise FetchError(str(exc)) from exc
    finally:
        if owns_client:
            await client.aclose()


async def fetch_readable(url: str) -> str:
    """JS-rendered, cleaned markdown via Jina Reader (free, no key). Used only when a plain
    fetch returns a JS shell, so we do not host a headless browser for the common case.
    """
    validate_url(url)
    async with _new_client(timeout=_READER_TIMEOUT, follow_redirects=True) as client:
        async with client.stream("GET", f"https://r.jina.ai/{url}") as resp:
            if resp.status_code >= 400:
                raise FetchError(f"HTTP {resp.status_code}")
            return await _read_capped(resp)


async def _read_sitemap(
    url: str, client: httpx.AsyncClient | None, depth: int
) -> list[str]:
    """Return real page URLs from a sitemap, recursing one level into a sitemap index.

    Many realtor stacks (WordPress+Yoast, Wix) serve a <sitemapindex> at /sitemap.xml whose
    <loc>s are child .xml sitemaps, not pages. Returning those directly would surface zero real
    listing URLs and pollute profile synthesis, so we expand the index and keep only page locs.
    """
    try:
        xml = await fetch_html(url, client)
    except FetchError:
        return []
    tree = HTMLParser(xml)
    if tree.css_first("sitemapindex") and depth > 0:
        children = [n.text(strip=True) for n in tree.css("loc") if n.text(strip=True)]
        out: list[str] = []
        for child in children[:_MAX_SITEMAPS]:
            out.extend(await _read_sitemap(child, client, depth - 1))
        return out
    return [
        loc
        for n in tree.css("loc")
        if (loc := n.text(strip=True)) and not loc.lower().endswith(".xml")
    ]


async def _sitemap_urls(seed_url: str, client: httpx.AsyncClient | None) -> list[str]:
    parts = urlparse(seed_url)
    return await _read_sitemap(
        f"{parts.scheme}://{parts.hostname}/sitemap.xml", client, depth=1
    )


async def _render_spa(seed_url: str, client: httpx.AsyncClient) -> list[CrawledPage]:
    """A client-rendered SPA seed (Wix/Squarespace/React): the page itself is a shell. The
    server-rendered sitemap.xml still lists the real sub-pages, so pull a tightly bounded set
    and render each through the reader instead of onboarding only the homepage.
    """
    urls: list[str] = [seed_url]
    for url in await _sitemap_urls(seed_url, client):
        if len(urls) >= _MAX_SPA_PAGES:
            break
        if url not in urls and same_host(seed_url, url):
            urls.append(url)

    semaphore = asyncio.Semaphore(_CONCURRENCY)

    async def _one(url: str) -> CrawledPage | None:
        async with semaphore:
            try:
                return CrawledPage(url, await fetch_readable(url), is_markdown=True)
            except (FetchError, httpx.HTTPError):
                return None

    rendered = await asyncio.gather(*(_one(u) for u in urls))
    pages = [p for p in rendered if p is not None]
    if pages:
        return pages
    # Sitemap yielded nothing usable: fall back to the seed alone via the reader.
    return [CrawledPage(seed_url, await fetch_readable(seed_url), is_markdown=True)]


async def crawl(seed_url: str, max_pages: int = _MAX_PAGES) -> list[CrawledPage]:
    """Fetch the seed plus a bounded set of same-host pages. If the seed is a JS shell, render
    it (and its sitemap sub-pages) through the reader since the DOM is client-generated.
    """
    validate_url(seed_url)
    async with _new_client(timeout=_TIMEOUT, follow_redirects=False) as client:
        seed_html = await fetch_html(seed_url, client)
        if looks_like_js_shell(seed_html):
            return await _render_spa(seed_url, client)

        candidates: list[str] = [seed_url]
        seen = {seed_url}
        for url in (await _sitemap_urls(seed_url, client)) + discover_links(
            seed_url, seed_html
        ):
            if len(candidates) >= max_pages:
                break
            if url not in seen and same_host(seed_url, url):
                seen.add(url)
                candidates.append(url)

        pages: list[CrawledPage] = [CrawledPage(seed_url, seed_html, is_markdown=False)]
        semaphore = asyncio.Semaphore(_CONCURRENCY)

        async def _one(url: str) -> CrawledPage | None:
            async with semaphore:
                try:
                    return CrawledPage(
                        url, await fetch_html(url, client), is_markdown=False
                    )
                except FetchError:
                    return None

        rest = await asyncio.gather(*(_one(u) for u in candidates[1:]))
        pages.extend(p for p in rest if p is not None)
        return pages
