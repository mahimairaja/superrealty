"""Integration: upsert a buyer then recall them by phone (returning-buyer recall).

Requires the live stack + OpenAI. Run via the integration gate.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.endpoints.buyers import router as buyers_router

pytestmark = pytest.mark.integration


async def test_upsert_then_recall_buyer():
    app = FastAPI()
    app.include_router(buyers_router, prefix="/api/v1")
    phone = "+1-519-555-0177"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        up = await c.post(
            "/api/v1/buyers",
            json={
                "phone": phone,
                "name": "Casey Buyer",
                "criteria": {"area": "Sarnia", "minBeds": 3},
            },
        )
        assert up.status_code == 201
        got = await c.get(f"/api/v1/buyers/{phone}")
    assert got.status_code == 200
    assert got.json()["found"] is True
