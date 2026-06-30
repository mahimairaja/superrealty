"""Telnyx v2 Messages client: the post-call lead handoff SMS to the realtor.

Best-effort; a failure never breaks the call close. The optional transport makes it
testable with httpx.MockTransport (no network, no real SMS).
"""

from __future__ import annotations

from typing import Any

import httpx

TELNYX_MESSAGES_URL = "https://api.telnyx.com/v2/messages"


async def send_sms(
    *,
    to: str,
    text: str,
    api_key: str,
    from_number: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"from": from_number, "to": to, "text": text}
    async with httpx.AsyncClient(timeout=20.0, transport=transport) as client:
        resp = await client.post(TELNYX_MESSAGES_URL, headers=headers, json=payload)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
    return data
