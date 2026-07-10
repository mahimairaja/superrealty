"""The Scheduling specialist: open showing times and booking, with a slot-id guard."""

from __future__ import annotations

import logging
import uuid

from livekit.agents import Agent, RunContext, function_tool

from src.agents.base_agent import RealtyBaseAgent
from src.agents.call_context import SCHEDULING, CallContext
from src.core.tool_tracing import traced_tool
from src.prompts.instructions import scheduling_instructions

logger = logging.getLogger("agent")


class SchedulingAgent(RealtyBaseAgent):
    ID = SCHEDULING
    ACTION = "Checking the calendar"

    def __init__(self, ctx: CallContext) -> None:
        super().__init__(ctx, instructions=scheduling_instructions(ctx.persona or None))

    @function_tool
    @traced_tool
    async def check_availability(self, context: RunContext) -> str:
        """Look up open showing times on the realtor's calendar. Offer only these times."""
        try:
            async with context.with_filler(
                "Let me check the calendar, one moment.", delay=2
            ):
                data = await self.ctx.api.check_availability()
        except Exception as exc:  # noqa: BLE001
            logger.warning("check_availability failed: %s", exc)
            return "I'm having trouble loading times. Can I take your details and follow up?"
        days = data.get("days", [])
        if not days:
            return "I don't see open times in the next week. Can I take your details and follow up?"
        self.ctx._offered_slots = {
            s["startUtc"] for d in days for s in d.get("slots", []) if s.get("startUtc")
        }
        lines = []
        for d in days:
            slots = [s for s in d.get("slots", []) if s.get("startUtc")]
            offered = ", ".join(f"{s['label']} (id {s['startUtc']})" for s in slots)
            lines.append(f"{d['date']}: {offered}")
        return (
            "Open showing times. Offer only these. When the caller picks one, call "
            "book_showing with the exact id shown in parentheses; never build the "
            "timestamp yourself.\n" + "\n".join(lines)
        )

    @function_tool
    @traced_tool
    async def book_showing(
        self,
        context: RunContext,
        property_code: str,
        start_utc: str,
        name: str,
        phone: str,
    ) -> str:
        """Book an in-person showing for a home at a chosen time. start_utc must be the
        exact id shown in parentheses next to the chosen time by check_availability
        (copy it verbatim; do not construct the timestamp from the spoken time).
        """
        if start_utc not in self.ctx._offered_slots:
            logger.warning("book_showing rejected unoffered start_utc=%r", start_utc)
            return (
                "I want to make sure that time is still open. Let me pull up the available "
                "showing times again and we'll pick one."
            )
        phone = phone or self.ctx.last_phone or ""
        if phone:
            self.ctx.last_phone = phone
        if self.ctx._booking_key is None:
            self.ctx._booking_key = str(uuid.uuid4())
        context.disallow_interruptions()
        try:
            async with context.with_filler("Locking that in, one moment.", delay=2):
                result = await self.ctx.api.book_showing(
                    {
                        "idempotency_key": self.ctx._booking_key,
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
        if status in ("accepted", "pending"):
            self.ctx.fire(
                self.ctx.push_event(
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
    async def to_concierge(self, context: RunContext) -> Agent:
        """Hand the call back to the concierge when the buyer is done booking."""
        from src.agents.concierge_agent import ConciergeAgent

        return self._handoff(ConciergeAgent(self.ctx))
