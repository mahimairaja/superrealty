import types

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.api.endpoints.settings as settings_mod
from src.api.endpoints.settings import router as settings_router
from src.core.clerk import get_current_tenant

TENANT = "org_settings_test"


def _client() -> AsyncClient:
    app = FastAPI()
    app.include_router(settings_router, prefix="/api/v1")
    app.dependency_overrides[get_current_tenant] = lambda: TENANT
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_get_and_update_settings(monkeypatch):
    store = {"sms_to": None}

    async def fake_get(org):
        assert org == TENANT  # scoped to the signed-in realtor
        return types.SimpleNamespace(sms_to=store["sms_to"])

    async def fake_set(org, sms_to):
        assert org == TENANT
        store["sms_to"] = sms_to
        return types.SimpleNamespace(sms_to=sms_to)

    monkeypatch.setattr(settings_mod.tenant_repository, "get_by_clerk_org_id", fake_get)
    monkeypatch.setattr(settings_mod.tenant_repository, "set_sms_to", fake_set)
    async with _client() as c:
        assert (await c.get("/api/v1/settings")).json()["sms_to"] is None
        patched = await c.patch("/api/v1/settings", json={"sms_to": "+1 519 555 0142"})
        assert patched.status_code == 200
        assert patched.json()["sms_to"] == "+1 519 555 0142"
        assert (await c.get("/api/v1/settings")).json()["sms_to"] == "+1 519 555 0142"


async def test_update_settings_rejects_a_bad_phone(monkeypatch):
    async def fake_set(org, sms_to):
        return types.SimpleNamespace(sms_to=sms_to)

    monkeypatch.setattr(settings_mod.tenant_repository, "set_sms_to", fake_set)
    async with _client() as c:
        resp = await c.patch("/api/v1/settings", json={"sms_to": "not a phone"})
    assert resp.status_code == 422


async def test_clearing_the_number_is_allowed(monkeypatch):
    async def fake_set(org, sms_to):
        return types.SimpleNamespace(sms_to=sms_to)

    monkeypatch.setattr(settings_mod.tenant_repository, "set_sms_to", fake_set)
    async with _client() as c:
        resp = await c.patch("/api/v1/settings", json={"sms_to": ""})
    assert resp.status_code == 200
    assert resp.json()["sms_to"] is None  # blank normalizes to unset
