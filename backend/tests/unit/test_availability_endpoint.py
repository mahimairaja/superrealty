import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.api.endpoints.availability as availability_mod
import src.core.widget_guard as widget_guard


@pytest.fixture(autouse=True)
def _reset_limiter():
    widget_guard._limiter = None
    yield
    widget_guard._limiter = None


def _client() -> AsyncClient:
    app = FastAPI()
    app.include_router(availability_mod.router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_availability_returns_days(monkeypatch):
    async def fake_slots(**kwargs):
        return [
            {
                "date": "2026-07-01",
                "slots": [{"startUtc": "2026-07-01T13:00:00Z", "label": "9:00 AM"}],
            }
        ]

    monkeypatch.setattr(availability_mod.config, "CAL_API_KEY", None, raising=False)
    # Force the configured branch by patching the secret accessor + event id.
    monkeypatch.setattr(availability_mod.cal_service, "get_available_slots", fake_slots)
    monkeypatch.setattr(
        availability_mod.config, "RR_CAL_EVENT_TYPE_ID", 123, raising=False
    )

    class _Key:
        @staticmethod
        def get_secret_value():
            return "k"

    monkeypatch.setattr(availability_mod.config, "CAL_API_KEY", _Key(), raising=False)
    async with _client() as c:
        resp = await c.get("/api/v1/availability")
    assert resp.status_code == 200
    body = resp.json()
    assert body["days"][0]["date"] == "2026-07-01"
    assert body["days"][0]["slots"][0]["label"] == "9:00 AM"


async def test_availability_empty_when_cal_unconfigured(monkeypatch):
    monkeypatch.setattr(availability_mod.config, "CAL_API_KEY", None, raising=False)
    monkeypatch.setattr(
        availability_mod.config, "RR_CAL_EVENT_TYPE_ID", None, raising=False
    )
    async with _client() as c:
        resp = await c.get("/api/v1/availability")
    assert resp.status_code == 200
    assert resp.json()["days"] == []
