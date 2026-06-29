import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.api.endpoints.calls as calls_mod
import src.core.widget_guard as widget_guard


class _Row:
    id = 7


class _FakeStore:
    def __init__(self) -> None:
        self.improved: list[str] = []

    async def improve(self, dataset: str) -> None:
        self.improved.append(dataset)


@pytest.fixture(autouse=True)
def _reset_limiter():
    widget_guard._limiter = None
    yield
    widget_guard._limiter = None


def _client() -> AsyncClient:
    app = FastAPI()
    app.include_router(calls_mod.router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_close_call_persists_and_improves(monkeypatch):
    captured: dict = {}

    async def fake_create(values: dict) -> _Row:
        captured.update(values)
        return _Row()

    store = _FakeStore()
    monkeypatch.setattr(calls_mod.call_log_repository, "create", fake_create)
    monkeypatch.setattr(calls_mod, "get_memory_store", lambda: store)

    async with _client() as c:
        resp = await c.post(
            "/api/v1/calls/room-1/close",
            json={"outcome": "completed", "buyer_phone": "+15195550100"},
        )
    assert resp.status_code == 200
    assert resp.json()["id"] == 7
    assert captured["room_name"] == "room-1"
    assert captured["outcome"] == "completed"
    # improve was folded in for the buyer's dataset
    assert store.improved == ["buyer-15195550100"]


async def test_close_call_without_phone_skips_improve(monkeypatch):
    async def fake_create(values: dict) -> _Row:
        return _Row()

    store = _FakeStore()
    monkeypatch.setattr(calls_mod.call_log_repository, "create", fake_create)
    monkeypatch.setattr(calls_mod, "get_memory_store", lambda: store)

    async with _client() as c:
        resp = await c.post("/api/v1/calls/room-2/close", json={"outcome": "abandoned"})
    assert resp.status_code == 200
    assert store.improved == []
