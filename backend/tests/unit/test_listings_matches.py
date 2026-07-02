# backend/tests/unit/test_listings_matches.py
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.api.endpoints.listings as listings_mod


def _client() -> AsyncClient:
    app = FastAPI()
    from src.core.clerk import get_current_tenant

    app.dependency_overrides[get_current_tenant] = lambda: "org_abc"
    app.include_router(listings_mod.router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_matches_returns_report_for_a_known_listing(monkeypatch):
    class _Store:
        async def list_listings(self, tenant_id):
            return [
                {
                    "code": "RR-102",
                    "address": "88 Maple",
                    "area": "Sarnia",
                    "beds": 3,
                    "price": 459000,
                }
            ]

    async def fake_report(tenant_id, listing):
        assert listing["code"] == "RR-102"
        return {
            "narrative": "Dana wants this",
            "buyers": [{"name": "Dana", "phone": "p"}],
            "count": 1,
        }

    monkeypatch.setattr(
        listings_mod, "get_memory_store", lambda: _Store(), raising=True
    )
    monkeypatch.setattr(
        listings_mod.get_graph_service(), "match_report", fake_report, raising=True
    )
    async with _client() as c:
        resp = await c.get("/api/v1/listings/RR-102/matches")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1


async def test_matches_404_for_unknown_listing(monkeypatch):
    class _Store:
        async def list_listings(self, tenant_id):
            return []

    monkeypatch.setattr(
        listings_mod, "get_memory_store", lambda: _Store(), raising=True
    )
    async with _client() as c:
        resp = await c.get("/api/v1/listings/NOPE/matches")
    assert resp.status_code == 404
