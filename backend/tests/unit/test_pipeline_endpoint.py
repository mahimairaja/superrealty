from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.api.endpoints.pipeline as pipeline_mod
from src.core.clerk import get_current_tenant

TENANT = "org_pipeline_test"


class _B:
    id = 1
    address = "1 Main St"
    status = "accepted"
    start_utc = None
    phone = "+1519"


class _C:
    id = 2
    room_name = "r1"
    outcome = "completed"
    buyer_phone = "+1519"
    ended_at = None


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(pipeline_mod.router, prefix="/api/v1")
    # Stand in for the Clerk-verified tenant so the test does not need a real JWT.
    app.dependency_overrides[get_current_tenant] = lambda: TENANT
    return app


async def test_pipeline_returns_bookings_and_calls_scoped_to_tenant(monkeypatch):
    seen: dict = {}

    async def fake_bookings(limit: int = 20, tenant_id=None):
        seen["bookings_tenant"] = tenant_id
        return [_B()]

    async def fake_calls(limit: int = 20, tenant_id=None):
        seen["calls_tenant"] = tenant_id
        return [_C()]

    monkeypatch.setattr(pipeline_mod.booking_repository, "list_recent", fake_bookings)
    monkeypatch.setattr(pipeline_mod.call_log_repository, "list_recent", fake_calls)
    async with AsyncClient(
        transport=ASGITransport(app=_app()), base_url="http://test"
    ) as c:
        resp = await c.get("/api/v1/pipeline")
    assert resp.status_code == 200
    body = resp.json()
    assert body["bookings"][0]["address"] == "1 Main St"
    assert body["calls"][0]["room_name"] == "r1"
    # Both reads were scoped to the signed-in realtor's tenant.
    assert seen == {"bookings_tenant": TENANT, "calls_tenant": TENANT}


async def test_pipeline_requires_authentication():
    # No dependency override: the Clerk dependency must reject an unauthenticated request
    # rather than leak another tenant's pipeline.
    app = FastAPI()
    app.include_router(pipeline_mod.router, prefix="/api/v1")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        resp = await c.get("/api/v1/pipeline")
    assert resp.status_code in (401, 403)
