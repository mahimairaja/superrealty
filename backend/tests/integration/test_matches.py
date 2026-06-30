"""Integration: a new listing matched against a remembered buyer returns a summary.

Cross-buyer matching is fuzzy (LLM completion over the graph), so this asserts the endpoint
returns a well-formed answer, not a specific buyer name. Run via the integration gate.
"""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.endpoints.matches import router as matches_router
from src.memory.store import get_memory_store

pytestmark = pytest.mark.integration


async def test_matches_returns_a_summary():
    store = get_memory_store()
    await store.upsert_buyer(
        {
            "phone": "+1-519-555-0188",
            "name": "Pat",
            "criteria": {"area": "Sarnia", "minBeds": 3},
        }
    )
    await store.add_listings(
        {"name": "Riley"},
        [
            {
                "code": "M1",
                "address": "9 Match St, Sarnia",
                "price": 430000,
                "beds": 3,
                "area": "Sarnia",
            }
        ],
    )
    app = FastAPI()
    app.include_router(matches_router, prefix="/api/v1")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.post(
            "/api/v1/matches", json={"area": "Sarnia", "beds": 3, "price": 430000}
        )
    assert resp.status_code == 200
    assert isinstance(resp.json()["summary"], str)
