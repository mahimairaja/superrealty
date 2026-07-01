"""Integration: a booking writes an idempotent Booking row, with cal.com stubbed.

Real DB + Cognee (the Showing node). cal.com is stub-the-send: no real booking is created.
Run via the integration gate.
"""

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.endpoints.bookings import router as bookings_router
from src.core.tenant import get_agent_tenant_id
from src.services import booking_service

pytestmark = pytest.mark.integration

TENANT = "org_bookings_integration"


async def test_booking_is_idempotent_with_cal_stubbed(monkeypatch):
    async def fake_cal(**kwargs):
        # Assert the request shape, return a canned cal.com confirmation. No real booking.
        assert kwargs["property_address"]
        return {
            "uid": "cal_test_1",
            "status": "accepted",
            "start": kwargs["start_utc_iso"],
            "end": None,
            "synced": True,
        }

    monkeypatch.setattr(booking_service.cal_service, "create_showing_booking", fake_cal)

    app = FastAPI()
    app.include_router(bookings_router, prefix="/api/v1")
    app.dependency_overrides[get_agent_tenant_id] = lambda: TENANT
    key = "idem-" + uuid.uuid4().hex[:8]
    body = {
        "idempotency_key": key,
        "property_code": "L1",
        "address": "1 Test St, Sarnia",
        "start": "2026-07-01T13:00:00Z",
        "timezone": "America/Toronto",
        "name": "Dana",
        "phone": "+15195550100",
    }
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        r1 = await c.post("/api/v1/bookings", json=body)
        assert r1.status_code == 201
        d1 = r1.json()
        assert d1["status"] == "accepted"
        assert d1["cal_uid"] == "cal_test_1"
        assert d1["synced"] is True

        # Same idempotency key -> same row, no second cal booking.
        r2 = await c.post("/api/v1/bookings", json=body)
        assert r2.status_code == 201
        assert r2.json()["id"] == d1["id"]
