import asyncio
import json

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

import src.api.endpoints.openorca as oo
from src.core.graph_token import openorca_tenant
from src.core.tenant import get_agent_tenant_id


def _app():
    app = FastAPI()
    app.include_router(oo.router, prefix="/api/v1")
    app.include_router(oo.state_router, prefix="/api/v1")
    app.dependency_overrides[openorca_tenant] = lambda: "org_a"
    app.dependency_overrides[get_agent_tenant_id] = lambda: "org_a"
    return app


async def test_events_emits_the_initial_snapshot_frame():
    oo.registry.reset()
    oo.registry.update("org_a", "t_org_a_1", active="concierge", action="Greeting")
    app = _app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        async with c.stream("GET", "/api/v1/openorca/events?token=x") as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    event = json.loads(line[len("data:") :].strip())
                    assert event["type"] == "snapshot.replace"
                    rooms = {m["id"] for m in event["snapshot"]["machines"]}
                    assert rooms == {"call:t_org_a_1"}
                    break


async def test_agent_state_push_reaches_an_open_stream():
    oo.registry.reset()
    app = _app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        async with c.stream("GET", "/api/v1/openorca/events?token=x") as resp:
            frames: list[dict] = []

            async def read_two():
                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        frames.append(json.loads(line[len("data:") :].strip()))
                        if len(frames) == 2:
                            return

            reader = asyncio.create_task(read_two())
            await asyncio.sleep(0.05)  # let the initial frame flush
            await c.post(
                "/api/v1/agent-state",
                json={
                    "room": "t_org_a_1",
                    "active": "property",
                    "action": "Searching",
                    "from": "concierge",
                },
            )
            await asyncio.wait_for(reader, timeout=2)
    # Second frame reflects the handoff.
    active = {a["id"]: a["status"] for a in frames[1]["snapshot"]["agents"]}
    assert active["t_org_a_1:property"] == "active"
