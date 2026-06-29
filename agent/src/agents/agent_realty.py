"""The realty voice agent.

Answers in the realtor's name, opens with the recording disclosure, qualifies the buyer
(budget, timeline, financing, area), and recommends homes drawn only from the realtor's
connected listings via the search_listings tool (backed by the Cognee recall endpoint).
A hard call-length cap bounds cost.
"""

from __future__ import annotations

import asyncio
import logging

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
        self, realtor: str | None = None, api: BackendApiClient | None = None
    ) -> None:
        super().__init__(instructions=REALTOR_INSTRUCTIONS)
        self._realtor = realtor or config.AGENT_NAME
        self._api = api or BackendApiClient()
        self._max_call_task: asyncio.Task | None = None
        self._ending = False

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
        """Find homes matching what the buyer wants, drawn only from the realtor's own
        connected listings. Pass the buyer's stated criteria as natural language
        (area, budget, bedrooms, and so on).
        """
        return await self._search(criteria)
