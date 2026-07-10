from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.api.endpoints.openorca as oo
from src.core.clerk import get_current_tenant
from src.core.graph_token import openorca_tenant
from src.core.tenant import get_agent_tenant_id


def _app():
    app = FastAPI()
    app.include_router(oo.router, prefix="/api/v1")
    app.include_router(oo.state_router, prefix="/api/v1")
    return app


def _client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def setup_function():
    oo.registry.reset()


async def test_agent_state_updates_the_registry():
    app = _app()
    app.dependency_overrides[get_agent_tenant_id] = lambda: "org_a"
    async with _client(app) as c:
        resp = await c.post(
            "/api/v1/agent-state",
            json={
                "room": "t_org_a_1",
                "active": "property",
                "action": "Searching",
                "from": "concierge",
            },
        )
    assert resp.status_code == 202
    calls = oo.registry.snapshot_calls("org_a")
    assert calls[0].active == "property"
    assert ("concierge", "property") in calls[0].edges


async def test_agent_state_rejects_an_unknown_agent():
    app = _app()
    app.dependency_overrides[get_agent_tenant_id] = lambda: "org_a"
    async with _client(app) as c:
        resp = await c.post(
            "/api/v1/agent-state",
            json={"room": "t_org_a_1", "active": "bogus", "action": "x"},
        )
    assert resp.status_code == 400


async def test_agent_state_requires_the_agent_secret():
    # No override: the real agent-secret gate runs and rejects a caller without the secret.
    app = _app()
    async with _client(app) as c:
        resp = await c.post(
            "/api/v1/agent-state",
            headers={"X-Tenant-Id": "org_a"},
            json={"room": "t_org_a_1", "active": "property", "action": "x"},
        )
    assert resp.status_code == 401


async def test_snapshot_is_scoped_to_the_token_tenant():
    oo.registry.update("org_a", "t_org_a_1", active="concierge", action="Greeting")
    oo.registry.update("org_b", "t_org_b_1", active="concierge", action="Greeting")
    app = _app()
    app.dependency_overrides[openorca_tenant] = lambda: "org_a"
    async with _client(app) as c:
        resp = await c.get("/api/v1/openorca/snapshot?token=x")
    assert resp.status_code == 200
    body = resp.json()
    rooms = {m["id"] for m in body["machines"]}
    assert rooms == {"call:t_org_a_1"}


async def test_runtime_info_advertises_sse_and_no_interventions():
    app = _app()
    app.dependency_overrides[openorca_tenant] = lambda: "org_a"
    async with _client(app) as c:
        resp = await c.get("/api/v1/openorca/runtime-info?token=x")
    body = resp.json()
    assert body["supports"]["sse"] is True
    assert body["supports"]["interventions"] is False


async def test_resolve_intervention_is_a_noop_200():
    app = _app()
    app.dependency_overrides[openorca_tenant] = lambda: "org_a"
    async with _client(app) as c:
        resp = await c.post(
            "/api/v1/openorca/interventions/resolve?token=x",
            json={"interventionId": "x", "action": "approve"},
        )
    assert resp.status_code == 200


async def test_graph_token_requires_the_console_and_returns_a_token():
    app = _app()
    app.dependency_overrides[get_current_tenant] = lambda: "org_a"
    async with _client(app) as c:
        resp = await c.get("/api/v1/openorca/graph-token")
    assert resp.status_code == 200
    assert resp.json()["token"]
