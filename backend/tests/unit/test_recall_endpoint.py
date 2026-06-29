import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.api.endpoints.recall as recall_mod
import src.core.widget_guard as widget_guard


class _FakeStore:
    async def recall(self, criteria, top_k=5):
        return ["A matching 3 bed home at 123 Maple Street, Sarnia"]


@pytest.fixture(autouse=True)
def _reset_limiter():
    widget_guard._limiter = None
    yield
    widget_guard._limiter = None


def _client(monkeypatch) -> AsyncClient:
    monkeypatch.setattr(recall_mod, "get_memory_store", lambda: _FakeStore())
    app = FastAPI()
    app.include_router(recall_mod.router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_recall_returns_grounded_answer(monkeypatch):
    async with _client(monkeypatch) as c:
        resp = await c.post(
            "/api/v1/recall",
            json={"realtor": "Riley", "criteria": {"area": "Sarnia", "minBeds": 3}},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["realtor"] == "Riley"
    assert "Maple" in body["answer"]
    assert body["match_count"] == 1


async def test_recall_accepts_free_text_criteria(monkeypatch):
    async with _client(monkeypatch) as c:
        resp = await c.post(
            "/api/v1/recall",
            json={"realtor": "Riley", "criteria": "3 bedroom near the park"},
        )
    assert resp.status_code == 200
    assert resp.json()["answer"]
