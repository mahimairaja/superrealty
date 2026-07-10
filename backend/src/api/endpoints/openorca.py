"""OpenOrca runtime contract for the realtor's live agent graph, plus the agent-state intake.

The voice worker POSTs which specialist holds each call to /agent-state (agent-secret gated).
The console reads its own tenant's live calls through the openorca-ui runtime contract
(snapshot / events / runtime-info / interventions-resolve), authorized by the ?token= graph
token because openorca-ui cannot send a bearer header. RealtyRecall models no interventions, so
resolve is a no-op stub.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.core.clerk import CurrentTenant
from src.core.graph_token import OpenOrcaTenant, mint_graph_token
from src.core.tenant import AgentTenant
from src.runtime.live_agents import AGENTS, registry
from src.runtime.openorca_mapper import to_snapshot

router = APIRouter(prefix="/openorca", tags=["openorca"])
state_router = APIRouter(tags=["openorca"])


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class AgentStateIn(BaseModel):
    room: str
    active: str
    action: str = ""
    from_: str | None = Field(default=None, alias="from")

    model_config = {"populate_by_name": True}


@state_router.post("/agent-state", status_code=status.HTTP_202_ACCEPTED)
async def agent_state(payload: AgentStateIn, tenant_id: AgentTenant) -> dict:
    if payload.active not in AGENTS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="unknown agent")
    registry.update(
        tenant_id,
        payload.room,
        active=payload.active,
        action=payload.action,
        from_agent=payload.from_,
    )
    await registry.publish(
        tenant_id,
        {
            "type": "snapshot.replace",
            "snapshot": to_snapshot(registry.snapshot_calls(tenant_id), _now_iso()),
        },
    )
    return {"ok": True}


@router.get("/graph-token")
async def graph_token(tenant_id: CurrentTenant) -> dict:
    """Mint the browser a short-lived token to read this tenant's live graph."""
    return {"token": mint_graph_token(tenant_id)}


@router.get("/snapshot")
async def snapshot(tenant_id: OpenOrcaTenant) -> dict:
    return to_snapshot(registry.snapshot_calls(tenant_id), _now_iso())


@router.get("/runtime-info")
async def runtime_info(tenant_id: OpenOrcaTenant) -> dict:
    return {
        "runtime": "realtyrecall",
        "language": "python",
        "supports": {"sse": True, "interventions": False, "snapshots": True},
    }


@router.post("/interventions/resolve")
async def resolve_intervention(tenant_id: OpenOrcaTenant) -> dict:
    # RealtyRecall has no interventions; the contract just wants the endpoint present.
    return {"ok": True}


def _sse(payload: object) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _event_stream(tenant_id: str) -> AsyncIterator[str]:
    q = registry.subscribe(tenant_id)
    try:
        # Emit the current snapshot immediately so a fresh subscriber renders without waiting.
        yield _sse(
            {
                "type": "snapshot.replace",
                "snapshot": to_snapshot(registry.snapshot_calls(tenant_id), _now_iso()),
            }
        )
        while True:
            try:
                payload = await asyncio.wait_for(q.get(), timeout=15.0)
                yield _sse(payload)
            except TimeoutError:
                # Keep-alive comment so proxies do not drop an idle connection.
                yield ": keep-alive\n\n"
    finally:
        registry.unsubscribe(tenant_id, q)


@router.get("/events")
async def events(tenant_id: OpenOrcaTenant) -> StreamingResponse:
    return StreamingResponse(
        _event_stream(tenant_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
