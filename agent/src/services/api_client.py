"""Async HTTP client for the realty backend (the memory + recall API).

The agent never calls Cognee, cal.com, or Telnyx directly. It calls the backend, which
mediates every side effect. The optional transport makes the client testable with
httpx.MockTransport (no network).
"""

from __future__ import annotations

from typing import Any

import httpx

from src.core.config import config


class BackendApiClient:
    def __init__(
        self,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        tenant_id: str | None = None,
    ) -> None:
        self._base_url = (base_url or config.BACKEND_URL).rstrip("/")
        self._transport = transport
        # The tenant this call belongs to (derived from the room name) and the shared agent
        # secret. Sent on every backend call: the tenant-scoped endpoints (recall, buyers)
        # require them, the widget-guarded ones (availability, bookings, close) ignore them.
        self._tenant_id = tenant_id
        self._agent_secret = config.AGENT_SERVICE_SECRET

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._tenant_id:
            headers["X-Tenant-Id"] = self._tenant_id
        if self._agent_secret:
            headers["X-Agent-Secret"] = self._agent_secret
        return headers

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0, transport=self._transport) as client:
            resp = await client.post(
                f"{self._base_url}{path}", json=body, headers=self._headers()
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
        return data

    async def _get(self, path: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0, transport=self._transport) as client:
            resp = await client.get(f"{self._base_url}{path}", headers=self._headers())
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
        return data

    async def recall(self, realtor: str, criteria: str) -> str:
        """Ask the backend to recall matching listings; return the grounded answer."""
        data = await self._post(
            "/api/v1/recall", {"realtor": realtor, "criteria": criteria}
        )
        return str(data.get("answer", ""))

    async def capture_lead(self, buyer: dict[str, Any]) -> dict[str, Any]:
        """Upsert a buyer keyed by phone."""
        return await self._post("/api/v1/buyers", buyer)

    async def check_availability(self) -> dict[str, Any]:
        """Open showing times on the realtor's calendar."""
        return await self._get("/api/v1/availability")

    async def book_showing(self, booking: dict[str, Any]) -> dict[str, Any]:
        """Book an in-person showing (idempotent by idempotency_key)."""
        return await self._post("/api/v1/bookings", booking)

    async def forget_buyer(self, phone: str) -> dict[str, Any]:
        """Forget a buyer on request (removes their Cognee dataset)."""
        async with httpx.AsyncClient(timeout=20.0, transport=self._transport) as client:
            resp = await client.delete(
                f"{self._base_url}/api/v1/buyers/{phone}", headers=self._headers()
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
        return data

    async def close_call(self, room: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist the call log and fold the conversation into permanent memory."""
        return await self._post(f"/api/v1/calls/{room}/close", payload)
