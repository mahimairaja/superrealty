"""Integration: closing a call persists a CallLog row (real DB).

Run via the integration gate.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.endpoints.calls import router as calls_router

pytestmark = pytest.mark.integration


async def test_close_call_persists_call_log():
    app = FastAPI()
    app.include_router(calls_router, prefix="/api/v1")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.post(
            "/api/v1/calls/room-int-1/close",
            json={"outcome": "completed", "duration_seconds": 42},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] is not None
    assert body["room_name"] == "room-int-1"
