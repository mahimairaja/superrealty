import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.api.endpoints.buyers as buyers_mod
import src.core.widget_guard as widget_guard


class _FakeStore:
    def __init__(self) -> None:
        self.upserts: list[dict] = []
        self.forgotten: str | None = None

    async def upsert_buyer(self, buyer: dict) -> dict:
        self.upserts.append(buyer)
        return buyer

    async def get_buyer(self, phone: str) -> dict:
        if "0100" in phone:
            return {
                "found": True,
                "phone": phone,
                "summary": "Dana, looking in Sarnia for 3 bedrooms.",
            }
        return {"found": False, "phone": phone}

    async def forget_buyer(self, phone: str) -> dict:
        self.forgotten = phone
        return {"forgotten": True, "phone": phone}


@pytest.fixture(autouse=True)
def _reset_limiter():
    widget_guard._limiter = None
    yield
    widget_guard._limiter = None


def _client(monkeypatch, store) -> AsyncClient:
    monkeypatch.setattr(buyers_mod, "get_memory_store", lambda: store)
    app = FastAPI()
    app.include_router(buyers_mod.router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_upsert_buyer(monkeypatch):
    store = _FakeStore()
    async with _client(monkeypatch, store) as c:
        resp = await c.post(
            "/api/v1/buyers",
            json={
                "phone": "+15195550100",
                "name": "Dana",
                "criteria": {"area": "Sarnia", "minBeds": 3},
            },
        )
    assert resp.status_code == 201
    assert resp.json()["phone"] == "+15195550100"
    assert store.upserts[0]["name"] == "Dana"
    assert store.upserts[0]["criteria"]["area"] == "Sarnia"


async def test_get_known_buyer_returns_summary(monkeypatch):
    async with _client(monkeypatch, _FakeStore()) as c:
        resp = await c.get("/api/v1/buyers/+15195550100")
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is True
    assert "Sarnia" in body["summary"]


async def test_get_unknown_buyer_is_not_found(monkeypatch):
    async with _client(monkeypatch, _FakeStore()) as c:
        resp = await c.get("/api/v1/buyers/+15190000000")
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is False
    assert body["summary"] is None


async def test_forget_buyer(monkeypatch):
    store = _FakeStore()
    async with _client(monkeypatch, store) as c:
        resp = await c.delete("/api/v1/buyers/+15195550100")
    assert resp.status_code == 200
    assert resp.json()["forgotten"] is True
    assert store.forgotten == "+15195550100"
