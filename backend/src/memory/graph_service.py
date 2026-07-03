"""Read-only views over the tenant's Cognee subgraph for the console.

This is the single surface the graph visualization, insights, and match cards read from. It
reuses store.py's Cognee configuration and NodeSet scoping so every read stays inside one
realtor's data.
"""

from __future__ import annotations

from typing import Any

import cognee
from cognee import SearchType
from cognee.infrastructure.databases.graph import get_graph_engine
from cognee.modules.engine.models import NodeSet

import src.memory.store as _store_module
from src import telemetry
from src.memory.store import ensure_cognee, tenant_tag


def _node_label(props: dict[str, Any]) -> str:
    """A short, human name for a node, by type. Address for a home, name for a person."""
    for key in ("address", "name", "code", "when_utc"):
        value = props.get(key)
        if value:
            return str(value)
    return str(props.get("id") or "node")


def _edge_triplet(edge: Any) -> tuple[str, str, str] | None:
    """Normalize a graph edge to (source, target, rel). Cognee edges are tuples whose first
    two items are the endpoint ids and whose third (when present) is the relationship name.
    """
    if not isinstance(edge, list | tuple) or len(edge) < 2:
        return None
    source, target = str(edge[0]), str(edge[1])
    rel = str(edge[2]) if len(edge) >= 3 and isinstance(edge[2], str) else "related"
    return source, target, rel


class GraphService:
    async def get_subgraph(self, tenant_id: str, *, cap: int = 150) -> dict[str, Any]:
        await ensure_cognee()
        graph = await get_graph_engine()
        raw_nodes, raw_edges = await graph.get_nodeset_subgraph(
            node_type=NodeSet, node_name=[tenant_tag(tenant_id)]
        )
        ordered = sorted(
            raw_nodes,
            key=lambda n: str((n[1] or {}).get("created_at") or ""),
            reverse=True,
        )
        nodes: list[dict[str, Any]] = []
        for node_id, props in ordered[:cap]:
            props = props or {}
            nodes.append(
                {
                    "id": str(node_id),
                    "label": _node_label(props),
                    "type": str(props.get("type") or "Node"),
                    "props": props,
                }
            )
        kept = {n["id"] for n in nodes}
        edges: list[dict[str, Any]] = []
        for raw in raw_edges or []:
            triplet = _edge_triplet(raw)
            if triplet is None:
                continue
            source, target, rel = triplet
            if source in kept and target in kept:
                edges.append({"source": source, "target": target, "rel": rel})
        return {"nodes": nodes, "edges": edges}

    _INSIGHT_PROMPTS = (
        (
            "What buyers want",
            "Across remembered buyers, what are they most asking for lately? One sentence.",
        ),
        (
            "Hot neighbourhoods",
            "Which neighbourhoods or areas are most in demand across buyers? One sentence.",
        ),
    )

    @telemetry.track("cognee.insights")
    async def insights(self, tenant_id: str) -> list[dict[str, Any]]:
        try:
            await ensure_cognee()
        except Exception:  # noqa: BLE001  (insights are best-effort; never raise)
            return []
        cards: list[dict[str, Any]] = []
        for title, prompt in self._INSIGHT_PROMPTS:
            try:
                results = await cognee.search(
                    query_text=prompt,
                    query_type=SearchType.GRAPH_SUMMARY_COMPLETION,
                    node_type=NodeSet,
                    node_name=[tenant_tag(tenant_id)],
                    top_k=3,
                )
            except Exception:  # noqa: BLE001
                continue
            body = str(results[0]).strip() if results else ""
            if body:
                cards.append({"title": title, "body": body})
        return cards

    async def match_report(
        self, tenant_id: str, listing: dict[str, Any]
    ) -> dict[str, Any]:
        store = _store_module.get_memory_store()
        narrative = await store.match_buyers(tenant_id, listing)
        buyers = await store.list_buyers(tenant_id)
        named = [
            {"name": b.get("name"), "phone": b.get("phone")}
            for b in buyers
            if b.get("name") and str(b["name"]).lower() in narrative.lower()
        ]
        return {"narrative": narrative, "buyers": named, "count": len(named)}


_service: GraphService | None = None


def get_graph_service() -> GraphService:
    global _service
    if _service is None:
        _service = GraphService()
    return _service
