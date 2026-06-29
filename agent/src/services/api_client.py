"""Async HTTP client for the realty backend (the memory + recall API).

The agent never calls Cognee, cal.com, or Telnyx directly. It calls the backend, which
mediates every side effect. The optional transport makes the client testable with
httpx.MockTransport (no network).
"""

from __future__ import annotations

import httpx

from src.core.config import config


class BackendApiClient:
    def __init__(
        self,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = (base_url or config.BACKEND_URL).rstrip("/")
        self._transport = transport

    async def recall(self, realtor: str, criteria: str) -> str:
        """Ask the backend to recall matching listings; return the grounded answer."""
        async with httpx.AsyncClient(timeout=20.0, transport=self._transport) as client:
            resp = await client.post(
                f"{self._base_url}/api/v1/recall",
                json={"realtor": realtor, "criteria": criteria},
            )
            resp.raise_for_status()
            data = resp.json()
        return str(data.get("answer", ""))
