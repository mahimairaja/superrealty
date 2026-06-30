"""Call-end observer: persist the call log and fold the conversation into memory.

Posted from the agent's shutdown callback. Best-effort: a failure never breaks teardown.
"""

from __future__ import annotations

import logging

from src.services.api_client import BackendApiClient

logger = logging.getLogger("agent")


async def post_call_log(
    api: BackendApiClient,
    room_name: str,
    *,
    outcome: str = "completed",
    buyer_phone: str | None = None,
) -> None:
    try:
        await api.close_call(
            room_name, {"outcome": outcome, "buyer_phone": buyer_phone}
        )
    except Exception as exc:  # noqa: BLE001  (best effort: never break teardown)
        logger.warning("post_call_log failed: %s", exc)
