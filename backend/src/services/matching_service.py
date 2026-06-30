"""Match a newly connected listing to waiting buyers (REQ-RR-MEM-002).

Thin wrapper over the memory store's graph search. POST-M0 note: buyers live in per-buyer
datasets (for forget); cross-buyer matching here relies on the typed Buyer nodes that
upsert also writes to the default graph, so matching quality improves as that graph grows.
"""

from __future__ import annotations

from typing import Any

from src.memory.store import get_memory_store


async def find_matches(listing: dict[str, Any]) -> dict[str, Any]:
    summary = await get_memory_store().match_buyers(listing)
    return {"summary": summary, "matched": bool(summary)}
