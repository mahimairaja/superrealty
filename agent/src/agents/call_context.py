"""Per-call shared state for the RealtyRecall specialists.

One CallContext is created when a call begins and passed into the Concierge, Property, and
Scheduling agents, so a handoff swaps the active Agent without ever dropping the tenant, the
caller's phone, the offered showing slots, the booking idempotency key, the cached catalog, or
the returning-buyer recall. All UI pushes and graph reports are best-effort: a slow or gone
browser (or a down backend) never adds latency to a voice turn and never raises into the call.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import voicegateway
from livekit.agents import get_job_context

from src.agents.listing_filters import (
    ListingSearchFilters,
    filter_listings,
    summarize_filters,
)
from src.core.config import config
from src.core.events import register_event_handlers
from src.prompts.instructions import _clean
from src.runtime.observers import post_call_log
from src.services.api_client import BackendApiClient
from src.utils.room import identify, resolve_tenant_id

logger = logging.getLogger("agent")

# Stable graph-node ids for the three specialists. These strings are the contract shared with
# the backend registry and the openorca-ui graph, so they must not drift.
CONCIERGE = "concierge"
PROPERTY = "property"
SCHEDULING = "scheduling"
AGENT_IDS = (CONCIERGE, PROPERTY, SCHEDULING)


class CallContext:
    def __init__(
        self,
        realtor: str | None = None,
        api: BackendApiClient | None = None,
        tenant_id: str | None = None,
        persona: dict[str, Any] | None = None,
        caller_phone: str | None = None,
    ) -> None:
        self.persona = persona or {}
        self.realtor = self.persona.get("name") or realtor or config.AGENT_NAME
        self.tenant_id = tenant_id
        self.api = api or BackendApiClient(tenant_id=tenant_id)
        # The buyer phone: known at connect for SIP (caller ID), else learned when a web caller
        # states it. Used for the call-log link AND to recall a returning buyer.
        self.last_phone: str | None = caller_phone
        # The LiveKit room name, set once in resolve(); the graph reporter keys on it.
        self.room: str | None = None
        # Which specialist currently holds the call (drives the glowing node).
        self.active: str = CONCIERGE
        # True once the one-time per-call setup (tenant/persona/attach/recall) has run.
        self.resolved: bool = False
        # The startUtc values check_availability offered this call; book_showing only accepts
        # one of these, so a hallucinated/misheard slot never reaches the calendar.
        self._offered_slots: set[str] = set()
        # One idempotency key per call, reused on a booking retry.
        self._booking_key: str | None = None
        # The structured listing catalog, fetched once and reused to push house cards.
        self._catalog: list[dict[str, Any]] | None = None
        # Whether we've already pulled this caller's remembered profile this call.
        self._recalled = False
        # The usage-summary logger from register_event_handlers, set in resolve().
        self._log_usage_summary: Callable[[], None] | None = None
        # Detached background tasks (held so they are not garbage-collected mid-flight).
        self._bg: set[asyncio.Task[Any]] = set()
        # The max-duration guard task, cancelled implicitly when the room closes.
        self._max_call_task: asyncio.Task[Any] | None = None
        # True once the call has been torn down, so teardown runs exactly once.
        self._closed = False

    def fire(self, coro: Any) -> None:
        """Run a coroutine in the background so it never adds latency to the voice turn."""
        task = asyncio.create_task(coro)
        self._bg.add(task)
        task.add_done_callback(self._bg.discard)

    def who(self) -> str:
        name = _clean(self.persona.get("name"))
        agency = _clean(self.persona.get("agency"))
        if name and agency:
            return f"{name}'s assistant at {agency}"
        if name:
            return f"{name}'s assistant"
        return "the realtor's assistant"

    def opener(self, recalled: str | None = None) -> str:
        """Greeting guidance, personalized to the realtor and to a returning buyer we remember."""
        who = self.who()
        if recalled:
            return (
                f"You are {who}. This is a returning caller we already remember. Greet them "
                "back warmly by name in one short sentence, briefly note what they were looking "
                "for, and ask how you can help today. Do not re-ask details we already have. "
                f"What we remember: {recalled}"
            )
        return (
            f"Greet the buyer warmly in one short sentence as {who} and ask what kind of "
            "home they are looking for."
        )

    def today_line(self) -> str:
        """A system-prompt line stating today's date so the model resolves relative dates."""
        try:
            now = datetime.now(ZoneInfo(config.TIMEZONE))
        except Exception:  # noqa: BLE001  (unknown tz -> local time is still useful)
            now = datetime.now()
        return f"\n\nFor date reasoning, today is {now:%A, %B} {now.day}, {now.year}."

    async def recall_returning_buyer(self) -> str | None:
        """Best-effort: pull what we remember about this caller (by phone). Once per call."""
        if self._recalled or not self.last_phone:
            return None
        if not (7 <= len(re.sub(r"\D", "", self.last_phone)) <= 15):
            return None
        self._recalled = True
        try:
            profile = await self.api.get_buyer_profile(self.last_phone)
        except Exception as exc:  # noqa: BLE001  (recall is best-effort; never break the call)
            logger.warning("buyer recall failed: %s", exc)
            return None
        if not profile.get("found"):
            return None
        name = str(profile.get("name") or "").strip()
        prefs = str(profile.get("prefs_summary") or "").strip()
        remembered = ". ".join(p for p in (name, prefs) if p)
        return remembered[:600] or None

    @staticmethod
    def caller_identity() -> str | None:
        try:
            room = get_job_context().room
        except Exception:  # noqa: BLE001  (no job context, e.g. a unit test)
            return None
        for participant in room.remote_participants.values():
            return str(participant.identity)
        return None

    async def push_event(self, event_type: str, data: Any) -> None:
        identity = self.caller_identity()
        if not identity:
            return
        try:
            await get_job_context().room.local_participant.perform_rpc(
                destination_identity=identity,
                method="onToolEvent",
                payload=json.dumps({"type": event_type, "data": data}),
                response_timeout=5.0,
            )
        except Exception as exc:  # noqa: BLE001  (UI push is best-effort)
            logger.debug("tool-event push failed: %s", exc)

    async def ensure_catalog(self) -> list[dict[str, Any]]:
        if self._catalog is None:
            try:
                self._catalog = await self.api.list_listings()
            except Exception as exc:  # noqa: BLE001
                logger.warning("catalog fetch failed: %s", exc)
                return []
        return self._catalog

    async def emit_shortlist(self, filters: ListingSearchFilters) -> None:
        catalog = await self.ensure_catalog()
        if not catalog:
            return
        matches = filter_listings(catalog, filters)
        label = summarize_filters(filters) or "all current listings"
        await self.push_event("shortlist", {"criteria": label, "matches": matches})

    # -------------------------------------------------------------------------
    # Graph reporter
    # -------------------------------------------------------------------------

    def report_state(
        self, active: str, action: str, from_agent: str | None = None
    ) -> None:
        """Record the now-active specialist and report it to the backend graph (best-effort)."""
        self.active = active
        if not self.room:
            return
        self.fire(self._report(self.room, active, action, from_agent))

    async def _report(
        self, room: str, active: str, action: str, from_agent: str | None
    ) -> None:
        try:
            await self.api.report_agent_state(
                room, active=active, action=action, from_agent=from_agent
            )
        except Exception as exc:  # noqa: BLE001  (graph reporting is best-effort)
            logger.debug("agent-state report failed: %s", exc)

    # -------------------------------------------------------------------------
    # Per-call lifecycle
    # -------------------------------------------------------------------------

    async def resolve(self, session: Any) -> None:
        """One-time per-call setup: tenant, caller, persona, telemetry, event handlers, and the
        max-call guard. Registers close() as a job shutdown callback so teardown runs once at
        session end (NOT on every handoff, unlike Agent.on_exit). Every step is best-effort."""
        ctx = get_job_context()
        room = ctx.room
        self.room = room.name
        self.tenant_id = resolve_tenant_id(
            room.name,
            getattr(ctx.job, "metadata", None),
            getattr(room, "metadata", None),
        )
        if not self.tenant_id:
            logger.warning("room %s has no tenant; memory tools unavailable", room.name)
        self.api = BackendApiClient(tenant_id=self.tenant_id)

        participant = session.room_io.linked_participant
        if participant is not None:
            caller = identify(participant)
            self.last_phone = caller.phone
            logger.info(
                "participant joined: kind=%s identity=%s", caller.kind, caller.identity
            )

        if self.tenant_id:
            try:
                persona = await self.api.get_realtor()
                self.persona = persona or {}
                self.realtor = self.persona.get("name") or config.AGENT_NAME
            except Exception as exc:  # noqa: BLE001  (persona is best-effort)
                logger.warning("realtor persona fetch failed: %s", exc)

        try:
            voicegateway.attach(
                session,
                project="realty-recall",
                agent_id=config.AGENT_NAME,
                tenant_id=self.tenant_id,
            )
        except Exception:  # noqa: BLE001  (telemetry is best-effort)
            logger.warning("voicegateway.attach failed", exc_info=True)

        self._log_usage_summary = register_event_handlers(session)
        self._max_call_task = asyncio.create_task(self._hang_up_max_duration())
        ctx.add_shutdown_callback(self.close)
        self.resolved = True

    async def _hang_up_max_duration(self) -> None:
        try:
            await asyncio.sleep(config.AGENT_MAX_CALL_SECONDS)
        except asyncio.CancelledError:
            return
        if self._closed:
            return
        try:
            await get_job_context().delete_room()
        except Exception as exc:  # noqa: BLE001
            logger.warning("max-duration delete_room failed: %s", exc)

    async def close(self, reason: str = "") -> None:
        """Per-call teardown, run exactly once (job shutdown callback): usage summary, persist
        the call log and fold the conversation into memory, then release the HTTP pool."""
        if self._closed:
            return
        self._closed = True
        # Cancel the max-call timer we own so it never lingers past teardown (the LiveKit
        # runtime also cancels it in production, but doing it here keeps close self-contained).
        if self._max_call_task is not None:
            self._max_call_task.cancel()
        if self._log_usage_summary is not None:
            self._log_usage_summary()
        if self.api is not None:
            try:
                if self.room:
                    await post_call_log(
                        self.api, self.room, buyer_phone=self.last_phone
                    )
            finally:
                await self.api.aclose()
