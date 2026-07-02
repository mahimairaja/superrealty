from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.api.endpoints.graph as graph_mod


def _client() -> AsyncClient:
    app = FastAPI()
    # Override the Clerk tenant dependency so the unit test needs no real JWT.
    from src.core.clerk import get_current_tenant

    app.dependency_overrides[get_current_tenant] = lambda: "org_abc"
    app.include_router(graph_mod.router, prefix="/api/v1")
    app.include_router(graph_mod.insights_router, prefix="/api/v1")
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_insights_endpoint_returns_cards(monkeypatch):
    async def fake_insights(tenant_id):
        return [{"title": "What buyers want", "body": "3-bed under 600k"}]

    monkeypatch.setattr(
        graph_mod.get_graph_service(), "insights", fake_insights, raising=True
    )
    async with _client() as c:
        resp = await c.get("/api/v1/insights")
    assert resp.status_code == 200
    assert resp.json()[0]["title"] == "What buyers want"


async def test_graph_endpoint_returns_subgraph(monkeypatch):
    async def fake_subgraph(tenant_id, *, cap=150):
        assert tenant_id == "org_abc"
        return {
            "nodes": [{"id": "1", "label": "88 Maple", "type": "Listing", "props": {}}],
            "edges": [],
        }

    monkeypatch.setattr(
        graph_mod.get_graph_service(), "get_subgraph", fake_subgraph, raising=True
    )
    async with _client() as c:
        resp = await c.get("/api/v1/graph")
    assert resp.status_code == 200
    body = resp.json()
    assert body["nodes"][0]["type"] == "Listing"
    assert body["edges"] == []
