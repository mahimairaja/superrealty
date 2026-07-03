from typing import Any

from fastapi import APIRouter

from src.core.clerk import CurrentTenant
from src.memory.graph_service import get_graph_service
from src.memory.store import get_memory_store

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
async def graph(tenant_id: CurrentTenant) -> dict[str, Any]:
    # The realtor's own memory subgraph (nodes + edges), scoped to their NodeSet. Rendered as
    # the live memory graph on the console.
    return await get_graph_service().get_subgraph(tenant_id)


@router.delete("")
async def reset_graph(tenant_id: CurrentTenant) -> dict[str, int]:
    # Wipe the realtor's own memory so they can re-onboard from scratch (demo reset). Console
    # authed and tenant-scoped: it only deletes nodes inside this realtor's NodeSet.
    removed = await get_memory_store().reset_tenant(tenant_id)
    return {"removed": removed}


insights_router = APIRouter(prefix="/insights", tags=["insights"])


@insights_router.get("")
async def insights(tenant_id: CurrentTenant) -> list[dict[str, Any]]:
    # Graph-wide market insights (Cognee SUMMARIES) for the realtor dashboard.
    return await get_graph_service().insights(tenant_id)
