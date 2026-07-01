from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.api.endpoints.listings as listings_mod
import src.api.endpoints.onboard as onboard_mod
import src.services.onboard_service as onboard_service
from src.api.endpoints.listings import router as listings_router
from src.api.endpoints.onboard import router as onboard_router
from src.core.clerk import get_current_tenant
from src.core.tenant import get_agent_tenant_id

FIXTURES = Path(__file__).parent.parent / "fixtures"

# Staging and the Cognee write are keyed by the Clerk-verified tenant; the test stands in
# for it so it does not need a real JWT, and the `realtor` form/query value is display-only.
TENANT = "org_onboard_test"

# One in-memory store shared across the app override and the reset fixture, so the suite
# exercises the real staging flow without a database (the DB-backed store runs in prod).
_TEST_STORE = onboard_service.InMemoryStagingStore()


@pytest.fixture(autouse=True)
async def _reset_state():
    await _TEST_STORE.clear()
    yield
    await _TEST_STORE.clear()


def _client() -> AsyncClient:
    app = FastAPI()
    app.include_router(onboard_router, prefix="/api/v1")
    app.include_router(listings_router, prefix="/api/v1")
    app.dependency_overrides[get_current_tenant] = lambda: TENANT
    app.dependency_overrides[onboard_service.get_staging_store] = lambda: _TEST_STORE
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_live_listings_returns_connected_homes(monkeypatch):
    seen = {}

    class _Store:
        async def list_listings(self, tenant_id):
            seen["tenant"] = tenant_id
            return [
                {
                    "code": "RR-101",
                    "address": "14 Zephyrwood Crescent, Sarnia",
                    "price": 389000.0,
                    "beds": 2,
                    "baths": 1.0,
                    "sqft": 980,
                    "description": "Bright starter condo",
                    "image_url": None,
                }
            ]

    monkeypatch.setattr(listings_mod, "get_memory_store", lambda: _Store())
    async with _client() as c:
        resp = await c.get("/api/v1/listings/live")
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["code"] == "RR-101"
    assert body[0]["beds"] == 2
    assert body[0]["price"] == 389000.0
    # Scoped to the signed-in realtor's tenant.
    assert seen["tenant"] == TENANT


async def test_listing_catalog_is_agent_authed(monkeypatch):
    seen = {}

    class _Store:
        async def list_listings(self, tenant_id):
            seen["tenant"] = tenant_id
            return [
                {
                    "code": "RR-102",
                    "address": "88 Maple Ridge Drive, Sarnia",
                    "price": 459000.0,
                    "beds": 3,
                    "baths": 2.0,
                    "sqft": 1520,
                    "description": "Classic brick bungalow",
                    "image_url": None,
                }
            ]

    monkeypatch.setattr(listings_mod, "get_memory_store", lambda: _Store())
    app = FastAPI()
    app.include_router(listings_router, prefix="/api/v1")
    app.dependency_overrides[get_agent_tenant_id] = lambda: "org_agent"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.get("/api/v1/listings/catalog")
    assert resp.status_code == 200
    assert resp.json()[0]["code"] == "RR-102"
    assert seen["tenant"] == "org_agent"


async def test_realtor_endpoint_is_agent_authed(monkeypatch):
    seen = {}

    class _Store:
        async def get_realtor(self, tenant_id):
            seen["tenant"] = tenant_id
            return {
                "name": "Morgan Bell",
                "agency": "Bluewater Homes",
                "area": "Sarnia",
                "tagline": "Homes with heart",
                "tone": "warm, local",
            }

    import src.api.endpoints.realtor as realtor_mod
    from src.api.endpoints.realtor import router as realtor_router

    monkeypatch.setattr(realtor_mod, "get_memory_store", lambda: _Store())
    app = FastAPI()
    app.include_router(realtor_router, prefix="/api/v1")
    app.dependency_overrides[get_agent_tenant_id] = lambda: "org_agent"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.get("/api/v1/realtor")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Morgan Bell"
    assert body["tone"] == "warm, local"
    assert seen["tenant"] == "org_agent"


async def test_realtor_me_is_console_authed(monkeypatch):
    seen = {}

    class _Store:
        async def get_realtor(self, tenant_id):
            seen["tenant"] = tenant_id
            return {
                "name": "Morgan Bell",
                "agency": "Bluewater Homes",
                "area": "Sarnia",
                "tagline": "Homes with heart",
                "tone": "warm, local",
            }

    import src.api.endpoints.realtor as realtor_mod
    from src.api.endpoints.realtor import router as realtor_router

    monkeypatch.setattr(realtor_mod, "get_memory_store", lambda: _Store())
    app = FastAPI()
    app.include_router(realtor_router, prefix="/api/v1")
    app.dependency_overrides[get_current_tenant] = lambda: TENANT
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.get("/api/v1/realtor/me")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Morgan Bell"
    assert seen["tenant"] == TENANT  # scoped to the signed-in realtor


async def test_confirm_persists_full_profile(monkeypatch):
    listing = {
        "code": "RR-1",
        "address": "88 Maple Ridge Drive, Sarnia",
        "price": 459000.0,
        "beds": 3,
        "baths": 2.0,
        "sqft": 1500,
        "image_url": None,
        "area": "Sarnia",
    }
    profile = {
        "name": "Riley Realty",
        "agency": "Blue Door",
        "area": "Sarnia",
        "tagline": "Homes with heart",
        "tone": "warm, professional",
    }
    captured = {}

    async def fake_ingest(url):
        return [listing], profile

    class _Mem:
        async def add_listings(self, tenant_id, realtor, drafts):
            captured["realtor"] = realtor
            return drafts

    monkeypatch.setattr(onboard_mod.ingest_service, "ingest_url", fake_ingest)
    monkeypatch.setattr(onboard_mod, "get_memory_store", lambda: _Mem())
    async with _client() as c:
        onb = await c.post(
            "/api/v1/onboard",
            data={"realtor": "", "authorized": "true", "url": "https://x.example"},
        )
        assert onb.status_code == 201
        conf = await c.post("/api/v1/onboard/confirm", data={"realtor": ""})
    assert conf.status_code == 200
    # The whole persona is persisted onto the Realtor node, not just the name.
    assert captured["realtor"]["name"] == "Riley Realty"
    assert captured["realtor"]["agency"] == "Blue Door"
    assert captured["realtor"]["tone"] == "warm, professional"


async def test_onboard_from_url_stages_listings_and_profile(monkeypatch):
    listing = {
        "code": "RR-1",
        "address": "88 Maple Ridge Drive, Sarnia",
        "price": 459000.0,
        "beds": 3,
        "baths": 2.0,
        "sqft": 1500,
        "description": "Brick bungalow",
        "image_url": None,
        "area": "Sarnia",
    }
    profile = {
        "name": "Riley Realty",
        "agency": "Blue Door",
        "area": "Sarnia",
        "tagline": "Homes with heart",
        "tone": "warm, professional",
    }

    async def fake_ingest(url):
        assert url == "https://riley.example"
        return [listing], profile

    monkeypatch.setattr(onboard_mod.ingest_service, "ingest_url", fake_ingest)
    async with _client() as c:
        resp = await c.post(
            "/api/v1/onboard",
            data={"realtor": "", "authorized": "true", "url": "https://riley.example"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["realtor"] == "Riley Realty"  # display name inferred from the site
    assert body["listings"][0]["address"].startswith("88 Maple")
    assert body["profile"]["tone"] == "warm, professional"


async def test_onboard_url_no_listings_returns_200_with_profile(monkeypatch):
    # A crawl that fetched fine but found no listings still succeeds and keeps the profile, so
    # the console can show the "no listings" state instead of a misleading fetch error.
    profile = {
        "name": "Riley Realty",
        "agency": None,
        "area": "Sarnia",
        "tagline": None,
        "tone": None,
    }

    async def fake_ingest(url):
        return [], profile

    monkeypatch.setattr(onboard_mod.ingest_service, "ingest_url", fake_ingest)
    async with _client() as c:
        resp = await c.post(
            "/api/v1/onboard",
            data={"realtor": "", "authorized": "true", "url": "https://riley.example"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["listings"] == []
    assert body["profile"]["name"] == "Riley Realty"
    assert body["realtor"] == "Riley Realty"


async def test_onboard_replaces_previous_staging(monkeypatch):
    # Re-fetching must replace, not accumulate: the set the realtor reviews is the set that
    # goes live, so a mistyped-then-corrected fetch cannot silently pile up stale drafts.
    batch = {"address": ""}

    async def fake_ingest(url):
        return [{"address": batch["address"]}], None

    monkeypatch.setattr(onboard_mod.ingest_service, "ingest_url", fake_ingest)
    async with _client() as c:
        batch["address"] = "1 First St"
        first = await c.post(
            "/api/v1/onboard", data={"authorized": "true", "url": "https://a.example"}
        )
        assert first.status_code == 201
        batch["address"] = "2 Second St"
        second = await c.post(
            "/api/v1/onboard", data={"authorized": "true", "url": "https://a.example"}
        )
        assert second.status_code == 201
        listed = await c.get("/api/v1/listings")
    assert [x["address"] for x in listed.json()] == ["2 Second St"]


async def test_onboard_without_url_or_file_is_400():
    async with _client() as c:
        resp = await c.post(
            "/api/v1/onboard", data={"realtor": "Riley", "authorized": "true"}
        )
    assert resp.status_code == 400


async def test_onboard_url_still_requires_consent():
    async with _client() as c:
        resp = await c.post(
            "/api/v1/onboard",
            data={
                "realtor": "Riley",
                "authorized": "false",
                "url": "https://x.example",
            },
        )
    assert resp.status_code == 403


async def test_onboard_requires_authorization():
    async with _client() as c:
        resp = await c.post(
            "/api/v1/onboard",
            data={"realtor": "Riley", "authorized": "false"},
            files={"file": ("jsonld.html", b"<html></html>", "text/html")},
        )
    assert resp.status_code == 403
    assert await _TEST_STORE.list(TENANT) == []


async def test_onboard_extracts_and_stages():
    html = (FIXTURES / "jsonld.html").read_bytes()
    async with _client() as c:
        resp = await c.post(
            "/api/v1/onboard",
            data={"realtor": "Riley", "authorized": "true"},
            files={"file": ("jsonld.html", html, "text/html")},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["realtor"] == "Riley"
    assert len(body["listings"]) == 1
    home = body["listings"][0]
    assert "123 Maple Street" in home["address"]
    assert home["price"] == 450000.0
    assert home["id"]


async def test_onboard_no_listings_is_422():
    async with _client() as c:
        resp = await c.post(
            "/api/v1/onboard",
            data={"realtor": "Riley", "authorized": "true"},
            files={
                "file": (
                    "empty.html",
                    b"<html><body>nothing</body></html>",
                    "text/html",
                )
            },
        )
    assert resp.status_code == 422


async def test_listings_get_patch_delete_roundtrip():
    csv_bytes = (FIXTURES / "listings.csv").read_bytes()
    async with _client() as c:
        onb = await c.post(
            "/api/v1/onboard",
            data={"realtor": "Riley", "authorized": "true"},
            files={"file": ("listings.csv", csv_bytes, "text/csv")},
        )
        assert onb.status_code == 201
        listings = onb.json()["listings"]
        assert len(listings) == 2
        first_id = listings[0]["id"]

        got = await c.get("/api/v1/listings", params={"realtor": "Riley"})
        assert got.status_code == 200
        assert len(got.json()) == 2

        patched = await c.patch(
            f"/api/v1/listings/{first_id}",
            params={"realtor": "Riley"},
            json={"price": 360000},
        )
        assert patched.status_code == 200
        assert patched.json()["price"] == 360000.0

        deleted = await c.delete(
            f"/api/v1/listings/{first_id}", params={"realtor": "Riley"}
        )
        assert deleted.status_code == 204

        after = await c.get("/api/v1/listings", params={"realtor": "Riley"})
        assert len(after.json()) == 1


async def test_patch_missing_listing_is_404():
    async with _client() as c:
        resp = await c.patch(
            "/api/v1/listings/nope", params={"realtor": "Riley"}, json={"price": 1}
        )
    assert resp.status_code == 404
