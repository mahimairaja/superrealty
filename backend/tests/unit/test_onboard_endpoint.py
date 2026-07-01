from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.api.endpoints.listings as listings_mod
import src.services.onboard_service as onboard_service
from src.api.endpoints.listings import router as listings_router
from src.api.endpoints.onboard import router as onboard_router
from src.core.clerk import get_current_tenant
from src.core.tenant import get_agent_tenant_id

FIXTURES = Path(__file__).parent.parent / "fixtures"

# Staging and the Cognee write are keyed by the Clerk-verified tenant; the test stands in
# for it so it does not need a real JWT, and the `realtor` form/query value is display-only.
TENANT = "org_onboard_test"


@pytest.fixture(autouse=True)
def _reset_state():
    onboard_service.get_staging_store().clear()
    yield
    onboard_service.get_staging_store().clear()


def _client() -> AsyncClient:
    app = FastAPI()
    app.include_router(onboard_router, prefix="/api/v1")
    app.include_router(listings_router, prefix="/api/v1")
    app.dependency_overrides[get_current_tenant] = lambda: TENANT
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


async def test_onboard_requires_authorization():
    async with _client() as c:
        resp = await c.post(
            "/api/v1/onboard",
            data={"realtor": "Riley", "authorized": "false"},
            files={"file": ("jsonld.html", b"<html></html>", "text/html")},
        )
    assert resp.status_code == 403
    assert onboard_service.get_staging_store().list(TENANT) == []


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
