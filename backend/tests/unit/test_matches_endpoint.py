import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.api.endpoints.matches as matches_mod
import src.core.widget_guard as widget_guard
import src.services.matching_service as matching_service


class _FakeStore:
    async def match_buyers(self, listing: dict) -> str:
        return "Pat is looking in Sarnia for 3 bedrooms; this home meets both."


@pytest.fixture(autouse=True)
def _reset_limiter():
    widget_guard._limiter = None
    yield
    widget_guard._limiter = None


def _client(monkeypatch) -> AsyncClient:
    monkeypatch.setattr(matching_service, "get_memory_store", lambda: _FakeStore())
    app = FastAPI()
    app.include_router(matches_mod.router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_matches_returns_summary(monkeypatch):
    async with _client(monkeypatch) as c:
        resp = await c.post(
            "/api/v1/matches", json={"area": "Sarnia", "beds": 3, "price": 430000}
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["matched"] is True
    assert "Sarnia" in body["summary"]


async def test_matches_empty_when_no_buyers(monkeypatch):
    class _Empty:
        async def match_buyers(self, listing: dict) -> str:
            return ""

    monkeypatch.setattr(matching_service, "get_memory_store", lambda: _Empty())
    app = FastAPI()
    app.include_router(matches_mod.router, prefix="/api/v1")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.post("/api/v1/matches", json={"area": "Nowhere"})
    assert resp.status_code == 200
    assert resp.json()["matched"] is False
