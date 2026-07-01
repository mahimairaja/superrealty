from src.services import ingest_service, llm_service
from src.services.fetch_service import CrawledPage


def test_dedupe_prefers_code_then_address():
    listings = [
        {"code": "A-1", "address": "1 St"},
        {"code": "A-1", "address": "1 St (dupe)"},  # same code -> dropped
        {"code": None, "address": "2 St"},
        {"code": None, "address": "2 st"},  # same address, case-insensitive -> dropped
        {"code": None, "address": None},  # no key -> dropped
    ]
    out = ingest_service._dedupe(listings)
    assert [x.get("code") or x.get("address") for x in out] == ["A-1", "2 St"]


def test_looks_like_listing_gate():
    assert ingest_service._looks_like_listing("Charming home, $459,000, 3 bed 2 bath")
    assert not ingest_service._looks_like_listing(
        "About us: we love Sarnia real estate"
    )
    assert not ingest_service._looks_like_listing("3 bedrooms available")  # no price


async def test_ingest_url_structured_pages_skip_the_llm(monkeypatch):
    # Two pages with JSON-LD listings; the LLM must NOT be called (cost guard).
    jsonld = (
        '<script type="application/ld+json">'
        '{"@type":"SingleFamilyResidence","name":"88 Maple, Sarnia",'
        '"numberOfBedrooms":3,"offers":{"price":459000}}</script>'
    )
    pages = [
        CrawledPage("https://x.example/a", f"<html>{jsonld}</html>", is_markdown=False),
        CrawledPage(
            "https://x.example/about", "<html><body>About us</body></html>", False
        ),
    ]
    monkeypatch.setattr(ingest_service.fetch_service, "crawl", lambda url: _aval(pages))

    called = {"n": 0}

    async def fake_extract(text):
        called["n"] += 1
        return []

    async def fake_profile(text):
        return {
            "name": "Riley",
            "agency": None,
            "area": "Sarnia",
            "tagline": None,
            "tone": None,
        }

    monkeypatch.setattr(llm_service, "extract_listings", fake_extract)
    monkeypatch.setattr(llm_service, "synthesize_profile", fake_profile)

    listings, profile = await ingest_service.ingest_url("https://x.example/a")
    assert len(listings) == 1
    assert "88 Maple" in listings[0]["address"]
    assert called["n"] == 0  # structured page never hit the LLM
    assert profile["name"] == "Riley"


async def test_multi_listing_index_routes_to_llm(monkeypatch):
    # An index page: one OG record but several priced cards in the body. The single structured
    # record is under-extraction, so the whole-page LLM read must run and win.
    html = (
        "<html><head>"
        '<meta property="og:title" content="Listings | Jane Realty" />'
        '<meta property="product:price:amount" content="400000" />'
        "</head><body>"
        "<div>101 A St $400,000 3 bed 2 bath</div>"
        "<div>202 B St $525,000 4 bed 3 bath</div>"
        "</body></html>"
    )
    pages = [CrawledPage("https://x.example/listings", html, is_markdown=False)]
    monkeypatch.setattr(ingest_service.fetch_service, "crawl", lambda url: _aval(pages))

    called = {"n": 0}

    async def fake_extract(text):
        called["n"] += 1
        return [
            {"address": "101 A St", "price": 400000},
            {"address": "202 B St", "price": 525000},
        ]

    async def fake_profile(text):
        return None

    monkeypatch.setattr(llm_service, "extract_listings", fake_extract)
    monkeypatch.setattr(llm_service, "synthesize_profile", fake_profile)

    listings, _ = await ingest_service.ingest_url("https://x.example/listings")
    assert called["n"] == 1  # single structured record treated as under-extraction
    assert {x["address"] for x in listings} == {"101 A St", "202 B St"}


async def _aval(value):
    return value
