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


class _Secret:
    def __init__(self, value: str) -> None:
        self._value = value

    def get_secret_value(self) -> str:
        return self._value


def _restrict_origins_and_secret(monkeypatch):
    # Reproduce production: an Origin allowlist is configured (so a browser without an allowed
    # Origin is rejected) and the shared agent secret is set.
    monkeypatch.setattr(
        availability_mod.config,
        "WIDGET_ALLOWED_ORIGINS_STR",
        "https://app.example",
        raising=False,
    )
    monkeypatch.setattr(
        availability_mod.config,
        "AGENT_SERVICE_SECRET",
        _Secret("s3cret"),
        raising=False,
    )
    monkeypatch.setattr(availability_mod.config, "CAL_API_KEY", None, raising=False)
    monkeypatch.setattr(
        availability_mod.config, "RR_CAL_EVENT_TYPE_ID", None, raising=False
    )


async def test_availability_403_for_server_caller_without_agent_secret(monkeypatch):
    # A caller with no allowed Origin and no agent secret is a browser off an unlisted site.
    _restrict_origins_and_secret(monkeypatch)
    async with _client() as c:
        resp = await c.get("/api/v1/availability")
    assert resp.status_code == 403


async def test_availability_allows_the_agent_secret_to_bypass_the_origin_guard(
    monkeypatch,
):
    # The voice worker has no browser Origin but presents the shared secret: it must get through
    # (the widget Origin guard is for public browser abuse, not our own backend-to-agent calls).
    _restrict_origins_and_secret(monkeypatch)
    async with _client() as c:
        resp = await c.get("/api/v1/availability", headers={"X-Agent-Secret": "s3cret"})
    assert resp.status_code == 200
    assert resp.json()["days"] == []  # cal.com unconfigured, so an empty slate


async def test_availability_rejects_a_wrong_agent_secret(monkeypatch):
    # A bad secret does not bypass; it falls through to the Origin check and is rejected.
    _restrict_origins_and_secret(monkeypatch)
    async with _client() as c:
        resp = await c.get("/api/v1/availability", headers={"X-Agent-Secret": "nope"})
    assert resp.status_code == 403
