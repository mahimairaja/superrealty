"""The Concierge: the supervisor the call starts on.

Owns the opening turn (recording disclosure + persona opener + returning-buyer recall), buyer
qualification, lead capture, and the forget-me request. Hands off to the Property or Scheduling
specialist when the conversation calls for it.
"""

from __future__ import annotations

import logging

from livekit.agents import Agent, RunContext, function_tool

from src.agents.base_agent import RealtyBaseAgent
from src.agents.call_context import CONCIERGE, CallContext
from src.core.tool_tracing import traced_tool
from src.prompts.instructions import concierge_instructions

logger = logging.getLogger("agent")

_RECORDING_NOTICE = (
    "Start by briefly and naturally letting the buyer know this call may be recorded for "
    "quality and training. Then continue: "
)


class ConciergeAgent(RealtyBaseAgent):
    ID = CONCIERGE
    ACTION = "Greeting the caller"

    def __init__(self, ctx: CallContext | None = None) -> None:
        resolved = ctx or CallContext()
        super().__init__(
            resolved, instructions=concierge_instructions(resolved.persona or None)
        )

    async def on_enter(self) -> None:
        if not self.ctx.resolved:
            # First entry this call: resolve the realtor/caller/persona, then open with the
            # recording disclosure and a persona-aware greeting.
            await self.ctx.resolve(self.session)
            await self.update_instructions(
                concierge_instructions(self.ctx.persona or None) + self.ctx.today_line()
            )
            recalled = await self.ctx.recall_returning_buyer()
            self.ctx.report_state(self.ID, self.ACTION)
            self.session.generate_reply(
                instructions=_RECORDING_NOTICE + self.ctx.opener(recalled)
            )
        else:
            # A later bounce back to the concierge (e.g. after scheduling): just report active.
            await super().on_enter()

    @function_tool
    @traced_tool
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
            self.ctx.last_phone = phone
        phone = phone or self.ctx.last_phone
        criteria: dict[str, object] = {}
        if area:
            criteria["area"] = area
        if max_price:
            criteria["maxPrice"] = max_price
        if min_beds:
            criteria["minBeds"] = min_beds
        try:
            await self.ctx.api.capture_lead(
                {"phone": phone or "", "name": name, "criteria": criteria or None}
            )
        except Exception as exc:  # noqa: BLE001  (degrade gracefully)
            logger.warning("capture_lead failed: %s", exc)
        self.ctx.fire(
            self.ctx.push_event(
                "lead", {"name": name, "phone": phone, "criteria": criteria or None}
            )
        )
        recalled = await self.ctx.recall_returning_buyer()
        if recalled:
            return (
                "This is a returning buyer we remember. Welcome them back by name and reuse "
                "what we already know instead of re-asking it. What we remember: "
                + recalled
            )
        return f"Thanks{', ' + name if name else ''}. I have your details."

    @function_tool
    @traced_tool
    async def forget_me(self, context: RunContext) -> str:
        """Forget everything we remember about THIS caller, at their request, and confirm.

        The phone is derived from the verified caller context (the number captured this
        call), never accepted as an argument, so a caller can only ever forget themselves.
        """
        phone = self.ctx.last_phone
        if not phone:
            return (
                "Could you share the phone number on your account so I can remove your "
                "information?"
            )
        try:
            await self.ctx.api.forget_buyer(phone)
        except Exception as exc:  # noqa: BLE001
            logger.warning("forget_me failed: %s", exc)
            return "I was not able to do that just now."
        self.ctx.last_phone = None
        return "Done. I have removed your information."

    @function_tool
    async def to_property(self, context: RunContext) -> Agent:
        """Hand the call to the property specialist when the buyer wants to search for, see, or
        hear about specific homes."""
        from src.agents.property_agent import PropertyAgent

        return self._handoff(PropertyAgent(self.ctx))

    @function_tool
    async def to_scheduling(self, context: RunContext) -> Agent:
        """Hand the call to the scheduling specialist when the buyer wants showing times or to
        book a visit."""
        from src.agents.scheduling_agent import SchedulingAgent

        return self._handoff(SchedulingAgent(self.ctx))
