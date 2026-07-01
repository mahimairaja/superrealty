"""The realty voice agent.

Answers in the realtor's name, opens with the recording disclosure, qualifies the buyer
(budget, timeline, financing, area), and recommends homes drawn only from the realtor's
connected listings via the search_listings tool (backed by the Cognee recall endpoint).
A hard call-length cap bounds cost.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from livekit.agents import Agent, RunContext, function_tool, get_job_context

from src.core.config import config
from src.prompts.instructions import REALTOR_INSTRUCTIONS
from src.services.api_client import BackendApiClient

logger = logging.getLogger("agent")

_RECORDING_NOTICE = (
    "Start by briefly and naturally letting the buyer know this call may be recorded for "
    "quality and training. Then continue: "
)
_DEFAULT_OPENER = (
    "Greet the buyer warmly in one short sentence as the realtor's assistant and ask what "
    "kind of home they are looking for."
)


class RealtyAgent(Agent):
    def __init__(
        self,
        realtor: str | None = None,
        api: BackendApiClient | None = None,
        tenant_id: str | None = None,
    ) -> None:
        super().__init__(instructions=REALTOR_INSTRUCTIONS)
        self._realtor = realtor or config.AGENT_NAME
        # The tenant (realtor's Clerk org) this call serves, derived from the room name. The
        # client presents it to the backend so memory reads/writes are scoped to this realtor.
        self._tenant_id = tenant_id
        self._api = api or BackendApiClient(tenant_id=tenant_id)
        self._max_call_task: asyncio.Task | None = None
        self._ending = False
        # One idempotency key per call, reused on a booking retry.
        self._booking_key: str | None = None
        # The buyer phone captured this call, for the call-log link on close.
        self.last_phone: str | None = None

    async def on_enter(self) -> None:
        # Cap call length so a stuck or abusive session cannot run up STT/LLM/TTS cost.
        self._max_call_task = asyncio.create_task(self._hang_up_max_duration())
        # The PIPEDA recording disclosure is always the first thing said.
        self.session.generate_reply(instructions=_RECORDING_NOTICE + _DEFAULT_OPENER)

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

    async def _search(self, criteria: str) -> str:
        """Recall matching listings from the backend (the realtor's connected set)."""
        try:
            return await self._api.recall(self._realtor, criteria)
        except Exception as exc:  # noqa: BLE001  (degrade gracefully)
            logger.warning("recall failed: %s", exc)
            return (
                "I'm having trouble pulling up listings right now. Can I take your "
                "details and follow up?"
            )

    @function_tool
    async def search_listings(self, context: RunContext, criteria: str) -> str:
        """Find homes from the realtor's own connected listings, and always call this
        before naming any home. For a specific ask, pass the buyer's stated criteria as
        natural language (area, budget, bedrooms, and so on). When the buyer wants to
        know what is available or to list everything, pass a broad query such as
        "all current listings" to get the full set instead of asking for criteria.
        """
        return await self._search(criteria)

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
        return f"Thanks{', ' + name if name else ''}. I have your details."

    @function_tool
    async def check_availability(self, context: RunContext) -> str:
        """Look up open showing times on the realtor's calendar. Offer only these times."""
        try:
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
        self.last_phone = phone
        if self._booking_key is None:
            self._booking_key = str(uuid.uuid4())
        try:
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
