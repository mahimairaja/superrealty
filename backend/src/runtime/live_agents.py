"""In-memory registry of live voice calls and which specialist currently holds each one.

Populated by POST /api/v1/agent-state from the voice worker and read by the tenant-scoped
OpenOrca endpoints. State is per backend process (no persistence): a call with no update within
the TTL is swept, so a dropped call never lingers on the realtor's graph. Each tenant has a set
of asyncio queues (one per open SSE connection) that publish() fans a payload out to.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass

AGENTS = ("concierge", "property", "scheduling")
DEFAULT_TTL_SECONDS = 600.0


@dataclass
class CallState:
    tenant_id: str
    room: str
    active: str
    action: str
    edges: set[tuple[str, str]]
    started_at: float
    updated_at: float


class LiveAgentRegistry:
    def __init__(
        self,
        now: Callable[[], float] = time.monotonic,
        ttl: float = DEFAULT_TTL_SECONDS,
    ) -> None:
        self._now = now
        self._ttl = ttl
        self._calls: dict[tuple[str, str], CallState] = {}
        self._queues: dict[str, set[asyncio.Queue]] = {}

    def update(
        self,
        tenant_id: str,
        room: str,
        active: str,
        action: str,
        from_agent: str | None = None,
    ) -> CallState:
        now = self._now()
        key = (tenant_id, room)
        state = self._calls.get(key)
        if state is None:
            state = CallState(
                tenant_id=tenant_id,
                room=room,
                active=active,
                action=action,
                edges=set(),
                started_at=now,
                updated_at=now,
            )
            self._calls[key] = state
        else:
            state.active = active
            state.action = action
            state.updated_at = now
        if from_agent and from_agent in AGENTS and from_agent != active:
            state.edges.add((from_agent, active))
        return state

    def _sweep(self) -> None:
        cutoff = self._now() - self._ttl
        # Sweep a call once it has gone at or past the TTL without an update (<=), so a call
        # aged exactly ttl seconds is dropped rather than lingering one more sweep cycle.
        stale = [k for k, s in self._calls.items() if s.updated_at <= cutoff]
        for k in stale:
            del self._calls[k]

    def snapshot_calls(self, tenant_id: str) -> list[CallState]:
        self._sweep()
        return [s for (tid, _), s in self._calls.items() if tid == tenant_id]

    def subscribe(self, tenant_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues.setdefault(tenant_id, set()).add(q)
        return q

    def unsubscribe(self, tenant_id: str, q: asyncio.Queue) -> None:
        subs = self._queues.get(tenant_id)
        if subs:
            subs.discard(q)
            if not subs:
                del self._queues[tenant_id]

    async def publish(self, tenant_id: str, payload: object) -> None:
        for q in list(self._queues.get(tenant_id, ())):
            await q.put(payload)

    def reset(self) -> None:
        self._calls.clear()
        self._queues.clear()


registry = LiveAgentRegistry()
