"""Integration: seed a listing then /recall surfaces a grounded answer.

Requires the live stack + OpenAI. Run via the integration gate.
"""

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.endpoints.recall import router as recall_router
from src.memory.store import get_memory_store

pytestmark = pytest.mark.integration


async def test_recall_surfaces_seeded_listing():
    tag = uuid.uuid4().hex[:8]
    await get_memory_store().add_listings(
        {"name": "Riley"},
        [
            {
                "code": f"R-{tag}",
                "address": f"{tag} Cedar Court, Sarnia",
                "price": 410000,
                "beds": 3,
                "baths": 2,
                "description": "Bright 3 bed near downtown",
                "area": "Sarnia",
            }
        ],
    )
    app = FastAPI()
    app.include_router(recall_router, prefix="/api/v1")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.post(
            "/api/v1/recall",
            json={"realtor": "Riley", "criteria": {"area": "Sarnia", "minBeds": 3}},
        )
    assert resp.status_code == 200
    assert resp.json()["answer"], "recall returned an empty answer"
