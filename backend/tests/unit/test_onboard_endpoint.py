from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.core.widget_guard as widget_guard
import src.services.onboard_service as onboard_service
from src.api.endpoints.listings import router as listings_router
from src.api.endpoints.onboard import router as onboard_router

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture(autouse=True)
def _reset_state():
    onboard_service.get_staging_store().clear()
    widget_guard._limiter = None
    yield
    onboard_service.get_staging_store().clear()
    widget_guard._limiter = None


def _client() -> AsyncClient:
    app = FastAPI()
    app.include_router(onboard_router, prefix="/api/v1")
    app.include_router(listings_router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_onboard_requires_authorization():
    async with _client() as c:
        resp = await c.post(
            "/api/v1/onboard",
            data={"realtor": "Riley", "authorized": "false"},
            files={"file": ("jsonld.html", b"<html></html>", "text/html")},
        )
    assert resp.status_code == 403
    assert onboard_service.get_staging_store().list("Riley") == []


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
