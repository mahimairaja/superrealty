"""Integration: onboard then confirm inserts the staged listings into the Cognee graph.

Requires the live stack + OpenAI. Run via the integration gate; the fast gate skips it.
"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.services.onboard_service as onboard_service
from src.api.endpoints.onboard import router as onboard_router

pytestmark = pytest.mark.integration

FIXTURES = Path(__file__).parent.parent / "fixtures"


async def test_onboard_then_confirm_inserts_into_memory():
    onboard_service.get_staging_store().clear()
    app = FastAPI()
    app.include_router(onboard_router, prefix="/api/v1")
    csv_bytes = (FIXTURES / "listings.csv").read_bytes()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        onb = await c.post(
            "/api/v1/onboard",
            data={"realtor": "Riley Confirm", "authorized": "true"},
            files={"file": ("listings.csv", csv_bytes, "text/csv")},
        )
        assert onb.status_code == 201
        assert len(onb.json()["listings"]) == 2

        confirmed = await c.post(
            "/api/v1/onboard/confirm", data={"realtor": "Riley Confirm"}
        )
    assert confirmed.status_code == 200
    assert confirmed.json()["inserted"] == 2
