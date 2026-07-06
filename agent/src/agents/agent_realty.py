"""The realty voice agent.

Answers in the realtor's name, opens with the recording disclosure, qualifies the buyer
(budget, timeline, financing, area), and recommends homes drawn only from the realtor's
connected listings via the search_listings tool (served from the realtor's fast structured
catalog, so a reply lands inside a normal voice turn). A hard call-length cap bounds cost.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import voicegateway
from livekit.agents import Agent, RunContext, function_tool, get_job_context

from src.agents.listing_filters import (
    ListingSearchFilters,
    filter_listings,
    summarize_filters,
)
from src.core.config import config
from src.core.events import register_event_handlers
from src.prompts.instructions import _clean, realtor_instructions
from src.runtime.observers import post_call_log
from src.services.api_client import BackendApiClient
from src.utils.room import identify, resolve_tenant_id

logger = logging.getLogger("agent")


def _find_listing(catalog: list[dict[str, Any]], home: str) -> dict[str, Any] | None:
    """Resolve a home the buyer names (by code or address substring) to a catalog entry."""
    needle = home.strip().lower()
    for h in catalog:
        if needle and needle == str(h.get("code") or "").lower():
            return h
    for h in catalog:
        if needle and needle in str(h.get("address") or "").lower():
            return h
    return None


def _format_listings_answer(matches: list[dict[str, Any]], total: int) -> str:
    """Turn the realtor's real catalog rows into one grounded, speakable answer.

    Built entirely from the structured catalog (a direct DB read), with no external recall or
    LLM synthesis, so a listings reply lands inside a normal voice turn and can never invent a
    home, price, or address. Names a handful and offers to go through the rest, matching the
    phone-call guidance in the system prompt.
    """
    if not matches:
        return (
            "I don't have a connected listing that fits that just now. I can take your "
            "details and follow up as soon as something matches."
        )

    def _price(h: dict[str, Any]) -> str:
        p = h.get("price")
        return f"${int(p):,}" if isinstance(p, int | float) else "price on request"

    shown = matches[:5]
    parts = []
    for h in shown:
        beds = h.get("beds")
        bed_txt = f", {beds} bed" if beds else ""
        parts.append(f"{h.get('address') or 'a home'} at {_price(h)}{bed_txt}")
    listing_text = "; ".join(parts)
    count = len(matches)
    if count >= total:
        head = (
            "I have one listing right now" if count == 1 else f"I have {count} listings"
        )
    else:
        head = "I found one that fits" if count == 1 else f"I found {count} that fit"
    tail = (
        f" There are {count - len(shown)} more I can go through."
        if count > len(shown)
        else ""
    )
    return f"{head}: {listing_text}.{tail}"


_RECORDING_NOTICE = (
    "Start by briefly and naturally letting the buyer know this call may be recorded for "
    "quality and training. Then continue: "
)


class RealtyAgent(Agent):
    def __init__(
        self,
        realtor: str | None = None,
        api: BackendApiClient | None = None,
        tenant_id: str | None = None,
        persona: dict[str, Any] | None = None,
        caller_phone: str | None = None,
    ) -> None:
        # The realtor's inferred persona (name/agency/area/tagline/tone) shapes both the system
        # prompt and the opener, so the assistant answers in their name and voice.
        self._persona = persona or {}
        super().__init__(instructions=realtor_instructions(persona))
        self._realtor = self._persona.get("name") or realtor or config.AGENT_NAME
        # The tenant (realtor's Clerk org) this call serves, derived from the room name. The
        # client presents it to the backend so memory reads/writes are scoped to this realtor.
        self._tenant_id = tenant_id
        self._api = api or BackendApiClient(tenant_id=tenant_id)
        self._max_call_task: asyncio.Task | None = None
        self._ending = False
        # One idempotency key per call, reused on a booking retry.
        self._booking_key: str | None = None
        # The buyer phone for this call: known at connect for SIP (caller ID), else learned when
        # a web caller states it. Used for the call-log link AND to recall a returning buyer.
        self.last_phone: str | None = caller_phone
        # Whether we've already pulled this caller's remembered profile this call (recall once).
        self._recalled = False
        # The structured listing catalog, fetched once and reused to push house cards.
        self._catalog: list[dict[str, Any]] | None = None
        # Detached UI-push tasks (held so they are not garbage-collected mid-flight).
        self._bg: set[asyncio.Task[Any]] = set()
        # Set in on_enter (per call): the usage-summary logger from register_event_handlers.
        self._log_usage_summary: Callable[[], None] | None = None

    def _fire(self, coro: Any) -> None:
        """Run a UI push in the background so it never adds latency to the voice turn (a slow
        or unanswering caller, e.g. SIP, would otherwise block the reply on the RPC timeout).
        """
        task = asyncio.create_task(coro)
        self._bg.add(task)
        task.add_done_callback(self._bg.discard)

    def _who(self) -> str:
        name = _clean(self._persona.get("name"))
        agency = _clean(self._persona.get("agency"))
        if name and agency:
            return f"{name}'s assistant at {agency}"
        if name:
            return f"{name}'s assistant"
        return "the realtor's assistant"

    def _opener(self, recalled: str | None = None) -> str:
        """Greeting guidance: personalized to the realtor, and to a returning buyer when we
        remember them (so the assistant welcomes them back instead of starting from scratch)."""
        who = self._who()
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

    def _today_line(self) -> str:
        """A system-prompt line stating today's date so the model resolves relative
        dates ("tomorrow", "next Tuesday"). Uses the configured timezone (the realtor's
        locale); falls back to naive local time if the zone name is unknown."""
        try:
            now = datetime.now(ZoneInfo(config.TIMEZONE))
        except Exception:  # noqa: BLE001  (unknown tz -> local time is still useful)
            now = datetime.now()
        return f"\n\nFor date reasoning, today is {now:%A, %B} {now.day}, {now.year}."

    async def _recall_returning_buyer(self) -> str | None:
        """Best-effort: pull what we remember about this caller (by phone) so the assistant can
        welcome them back and reuse prior criteria. Recalls once per call; None if new/unknown.
        """
        if self._recalled or not self.last_phone:
            return None
        # Only look up a plausible phone (7-15 digits): the number can arrive from an LLM tool
        # arg, so this rejects garbage before it reaches the backend. Leave _recalled unset on a
        # bad value so a later, valid number can still recall.
        if not (7 <= len(re.sub(r"\D", "", self.last_phone)) <= 15):
            return None
        self._recalled = True
        try:
            data = await self._api.get_buyer(self.last_phone)
        except Exception as exc:  # noqa: BLE001  (recall is best-effort; never break the call)
            logger.warning("buyer recall failed: %s", exc)
            return None
        if not data.get("found"):
            return None
        summary = str(data.get("summary") or "").strip()
        nearby = str(data.get("nearby") or "").strip()
        if nearby:
            summary = f"{summary} Also worth mentioning: {nearby}".strip()
        return summary[:600] or None

    async def on_enter(self) -> None:
        # Per-call setup, moved here from the old entrypoint: the AgentPool uses one
        # universal entrypoint, so each call resolves its own realtor post-connect.
        await self._resolve_call_context()
        # System prompt = persona (answer in the realtor's name) + today's date (so
        # "tomorrow" / "next Tuesday" resolve). Set here, after resolve, so date
        # grounding holds even when the persona fetch failed.
        await self.update_instructions(
            realtor_instructions(self._persona or None) + self._today_line()
        )
        # Cap call length so a stuck or abusive session cannot run up STT/LLM/TTS cost.
        self._max_call_task = asyncio.create_task(self._hang_up_max_duration())
        # A SIP caller's number is known at connect, so we can recognize a returning buyer
        # before the first word. (Web callers are recalled once they give their number below.)
        recalled = await self._recall_returning_buyer()
        # The PIPEDA recording disclosure is always the first thing said.
        self.session.generate_reply(
            instructions=_RECORDING_NOTICE + self._opener(recalled)
        )

    async def _resolve_call_context(self) -> None:
        """Resolve the realtor (tenant), caller, persona, and telemetry for this call.

        Runs once at the start of every call; was the entrypoint's job before the
        AgentPool migration. Every step is best-effort so a backend hiccup or an odd
        room never blocks the greeting.
        """
        ctx = get_job_context()
        room = ctx.room
        self._tenant_id = resolve_tenant_id(
            room.name,
            getattr(ctx.job, "metadata", None),
            getattr(room, "metadata", None),
        )
        if not self._tenant_id:
            logger.warning("room %s has no tenant; memory tools unavailable", room.name)
        self._api = BackendApiClient(tenant_id=self._tenant_id)

        # Identify the caller. A SIP caller's number is known now (caller ID); a web
        # caller's is learned when they state it. linked_participant is None in console
        # mode or before a caller joins, so guard it.
        participant = self.session.room_io.linked_participant
        if participant is not None:
            caller = identify(participant)
            self.last_phone = caller.phone
            logger.info(
                "participant joined: kind=%s identity=%s", caller.kind, caller.identity
            )

        # The realtor's synthesized persona so the assistant answers in their name/voice.
        if self._tenant_id:
            try:
                persona = await self._api.get_realtor()
                self._persona = persona or {}
                self._realtor = self._persona.get("name") or config.AGENT_NAME
            except Exception as exc:  # noqa: BLE001  (persona is best-effort)
                logger.warning("realtor persona fetch failed: %s", exc)

        # Observe this call with VoiceGateway: per-turn STT/LLM/TTS cost + latency,
        # attributed to this realtor (tenant) under the realty-recall project.
        try:
            voicegateway.attach(
                self.session,
                project="realty-recall",
                agent_id=config.AGENT_NAME,
                tenant_id=self._tenant_id,
            )
        except Exception:  # noqa: BLE001  (telemetry is best-effort)
            logger.warning("voicegateway.attach failed", exc_info=True)

        self._log_usage_summary = register_event_handlers(self.session)

    async def on_exit(self) -> None:
        # Per-call teardown (was the entrypoint's shutdown callback): log the usage
        # summary, then persist the call log and fold the conversation into memory.
        if self._log_usage_summary is not None:
            self._log_usage_summary()
        if self._api is not None:
            try:
                await post_call_log(
                    self._api, get_job_context().room.name, buyer_phone=self.last_phone
                )
            finally:
                # Release the shared HTTP connection pool for this call (#11).
                await self._api.aclose()

    async def _hang_up_max_duration(self) -> None:
        try:
            await asyncio.sleep(config.AGENT_MAX_CALL_SECONDS)
        except asyncio.CancelledError:
            return  # the call ended before the cap
        if self._ending:
            return
        self._ending = True
        try:
            await self.session.say(
                "We've reached the end of this session. Thanks for calling, and goodbye.",
                allow_interruptions=False,
            )
        except Exception as exc:  # noqa: BLE001  (best effort: still hang up)
            logger.warning("max-duration goodbye failed: %s", exc)
        try:
            await get_job_context().delete_room()
        except Exception as exc:  # noqa: BLE001
            logger.warning("max-duration delete_room failed: %s", exc)

    async def _listings_answer(self, filters: ListingSearchFilters) -> str:
        """Answer a listings question from the realtor's fast structured catalog.

        The catalog is a direct DB read (sub-second), unlike the Cognee recall endpoint whose
        graph+vector+LLM synthesis runs 10-20s and blows the voice turn's timeout. Answering
        from the catalog keeps replies inside a normal turn while staying fully grounded in the
        realtor's real, connected listings. The parsed filters are read back as a lead-in
        ("in Sarnia, 3+ beds, under $480,000:") so the buyer hears their criteria confirmed.
        """
        catalog = await self._ensure_catalog()
        if not catalog:
            return (
                "I'm having a little trouble pulling up listings right now. Can I take "
                "your details and follow up?"
            )
        matches = filter_listings(catalog, filters)
        answer = _format_listings_answer(matches, len(catalog))
        echo = summarize_filters(filters)
        return f"{echo[0].upper()}{echo[1:]}: {answer}" if echo else answer

    # ---- Live UI: push tool events to the caller's screen -------------------
    # The buyer's browser registers an "onToolEvent" RPC method; we call it as tools run so
    # house cards, the booking, and the simulated SMS appear in sync with the conversation.
    # Best-effort: a failed push (slow or gone browser) never breaks the voice turn.

    @staticmethod
    def _caller_identity() -> str | None:
        try:
            room = get_job_context().room
        except Exception:  # noqa: BLE001  (no job context, e.g. console mode)
            return None
        for participant in room.remote_participants.values():
            return str(participant.identity)
        return None

    async def _push_event(self, event_type: str, data: Any) -> None:
        identity = self._caller_identity()
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

    async def _ensure_catalog(self) -> list[dict[str, Any]]:
        if self._catalog is None:
            try:
                self._catalog = await self._api.list_listings()
            except Exception as exc:  # noqa: BLE001
                # Leave the cache unset so a later tool call retries rather than being stuck
                # with an empty catalog for the rest of the call after one transient failure.
                logger.warning("catalog fetch failed: %s", exc)
                return []
        return self._catalog

    async def _emit_shortlist(self, filters: ListingSearchFilters) -> None:
        catalog = await self._ensure_catalog()
        if not catalog:
            return
        matches = filter_listings(catalog, filters)
        label = summarize_filters(filters) or "all current listings"
        await self._push_event("shortlist", {"criteria": label, "matches": matches})

    @function_tool
    async def search_listings(
        self,
        context: RunContext,
        min_beds: int | None = None,
        min_baths: float | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        area: str | None = None,
        min_sqft: int | None = None,
        max_sqft: int | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> str:
        """Find homes from the realtor's own connected listings, and always call this
        before naming any home. Fill only the fields the buyer stated: min_beds,
        min_baths, min_price and max_price in dollars, area (a neighbourhood or city),
        min_sqft and max_sqft. Leave every field blank to list all current listings
        rather than asking for criteria first. Optionally sort_by one of "price",
        "beds", or "sqft" with sort_order "asc" or "desc".
        """
        filters = ListingSearchFilters(
            min_beds=min_beds,
            min_baths=min_baths,
            min_price=min_price,
            max_price=max_price,
            area=area,
            min_sqft=min_sqft,
            max_sqft=max_sqft,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        answer = await self._listings_answer(filters)
        self._fire(self._emit_shortlist(filters))
        return answer

    @function_tool
    async def show_home(self, context: RunContext, home: str) -> str:
        """Pull ONE specific home up on the buyer's screen with its photo and full details.
        Call this whenever the buyer asks about a particular home or you are describing one in
        depth. `home` is the address or the listing code (e.g. "88 Maple Ridge" or "RR-102").
        """
        listing = _find_listing(await self._ensure_catalog(), home)
        if not listing:
            return "I couldn't find that exact home. Want me to list what's available?"
        self._fire(self._push_event("property", listing))
        beds = listing.get("beds")
        price = listing.get("price")
        price_txt = (
            f"${int(price):,}" if isinstance(price, int | float) else "price on request"
        )
        return (
            f"Putting {listing.get('address')} on your screen now: {price_txt}"
            f"{f', {beds} bed' if beds else ''}. {listing.get('description') or ''}"
        )

    @function_tool
    async def capture_lead(
        self,
        context: RunContext,
        name: str | None = None,
        phone: str | None = None,
        area: str | None = None,
        max_price: int | None = None,
        min_beds: int | None = None,
    ) -> str:
        """Record the buyer's contact details (name, phone) and what they are looking for
        (area, budget, bedrooms). Safe to call again as details firm up.
        """
        if phone:
            self.last_phone = phone
        # Fall back to a number the buyer entered before the call (their caller ID / the call
        # screen's phone prompt), so they are remembered even if they never say it aloud.
        phone = phone or self.last_phone
        criteria: dict[str, object] = {}
        if area:
            criteria["area"] = area
        if max_price:
            criteria["maxPrice"] = max_price
        if min_beds:
            criteria["minBeds"] = min_beds
        try:
            await self._api.capture_lead(
                {"phone": phone or "", "name": name, "criteria": criteria or None}
            )
        except Exception as exc:  # noqa: BLE001  (degrade gracefully)
            logger.warning("capture_lead failed: %s", exc)
        self._fire(
            self._push_event(
                "lead", {"name": name, "phone": phone, "criteria": criteria or None}
            )
        )
        # A web caller has no caller ID, so this is the first moment we can recognize a
        # returning buyer. Recall once and, if we know them, tell the model to welcome them back.
        recalled = await self._recall_returning_buyer()
        if recalled:
            return (
                "This is a returning buyer we remember. Welcome them back by name and reuse "
                "what we already know instead of re-asking it. What we remember: "
                + recalled
            )
        return f"Thanks{', ' + name if name else ''}. I have your details."

    @function_tool
    async def check_availability(self, context: RunContext) -> str:
        """Look up open showing times on the realtor's calendar. Offer only these times."""
        try:
            # An async-tool filler (livekit-agents 1.6+): if the calendar round-trip runs long
            # and the line goes quiet, the caller hears a short "one moment" instead of dead air.
            async with context.with_filler(
                "Let me check the calendar, one moment.", delay=2
            ):
                data = await self._api.check_availability()
        except Exception as exc:  # noqa: BLE001
            logger.warning("check_availability failed: %s", exc)
            return "I'm having trouble loading times. Can I take your details and follow up?"
        days = data.get("days", [])
        if not days:
            return "I don't see open times in the next week. Can I take your details and follow up?"
        lines = [
            f"{d['date']}: {', '.join(s['label'] for s in d['slots'])}" for d in days
        ]
        return "Open showing times, offer only these:\n" + "\n".join(lines)

    @function_tool
    async def book_showing(
        self,
        context: RunContext,
        property_code: str,
        start_utc: str,
        name: str,
        phone: str,
    ) -> str:
        """Book an in-person showing for a home at a chosen time. start_utc is one of the
        startUtc values from check_availability.
        """
        # Fall back to a number entered before the call so a booking still carries a phone even
        # if the buyer never spoke it (the call screen's phone prompt / SIP caller ID).
        phone = phone or self.last_phone or ""
        if phone:
            self.last_phone = phone
        if self._booking_key is None:
            self._booking_key = str(uuid.uuid4())
        # Booking is a write to the realtor's calendar: don't let a stray word cut it off
        # half-done, and cover the round-trip with a filler so the caller never hears silence.
        context.disallow_interruptions()
        try:
            async with context.with_filler("Locking that in, one moment.", delay=2):
                result = await self._api.book_showing(
                    {
                        "idempotency_key": self._booking_key,
                        "property_code": property_code,
                        "start": start_utc,
                        "name": name,
                        "phone": phone,
                    }
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("book_showing failed: %s", exc)
            return "That did not go through. Can I take your number and have someone follow up?"
        status = result.get("status")
        # Only surface a booking card/text for a real booking or request. A rejected slot (the
        # time was taken) must NOT push a "booked" card, or the caller's screen would contradict
        # what the assistant just said. The reply below then offers other times.
        if status in ("accepted", "pending"):
            self._fire(
                self._push_event(
                    "booking",
                    {
                        "propertyCode": property_code,
                        "address": result.get("address"),
                        "startUtc": start_utc,
                        "status": status,
                        "synced": bool(result.get("synced")),
                    },
                )
            )
        if status == "accepted" and result.get("synced"):
            return "You are all set. The showing is booked."
        if status in ("accepted", "pending"):
            return "I have put in the request and we will confirm it shortly."
        return "That time did not work out. Want me to check other times?"

    @function_tool
    async def forget_me(self, context: RunContext) -> str:
        """Forget everything we remember about THIS caller, at their request, and confirm.

        The phone is derived from the verified caller context (the number captured this
        call), never accepted as an argument, so a caller can only ever forget themselves.
        """
        phone = self.last_phone
        if not phone:
            return (
                "Could you share the phone number on your account so I can remove your "
                "information?"
            )
        try:
            await self._api.forget_buyer(phone)
        except Exception as exc:  # noqa: BLE001
            logger.warning("forget_me failed: %s", exc)
            return "I was not able to do that just now."
        self.last_phone = None
        return "Done. I have removed your information."
