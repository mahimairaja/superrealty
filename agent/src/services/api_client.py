"""Async HTTP client for the realty backend (the memory + recall API).

The agent never calls Cognee, cal.com, or Telnyx directly. It calls the backend, which
mediates every side effect. The optional transport makes the client testable with
httpx.MockTransport (no network).
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from src.core.config import config


class BackendApiClient:
    def __init__(
        self,
        base_url: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        tenant_id: str | None = None,
    ) -> None:
        # Every client path already carries /api/v1, so strip it if the configured base URL
        # includes it too. A BACKEND_URL set either way ("https://host" or
        # "https://host/api/v1") then works instead of 404ing on /api/v1/api/v1/... paths.
        base = (base_url or config.BACKEND_URL).rstrip("/")
        if base.endswith("/api/v1"):
            base = base[: -len("/api/v1")]
        self._base_url = base
        self._transport = transport
        # The tenant this call belongs to (derived from the room name) and the shared agent
        # secret. Sent on every backend call: the tenant-scoped endpoints (recall, buyers,
        # bookings) require them, the widget-guarded ones (availability, close) ignore them.
        self._tenant_id = tenant_id
        self._agent_secret = config.AGENT_SERVICE_SECRET
        # One AsyncClient (connection pool) for this client's lifetime instead of a
        # fresh one per request. Created lazily on first use; closed by ``aclose`` on
        # call teardown (RealtyAgent.on_exit).
        self._client: httpx.AsyncClient | None = None

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._tenant_id:
            headers["X-Tenant-Id"] = self._tenant_id
        if self._agent_secret:
            headers["X-Agent-Secret"] = self._agent_secret
        return headers

    def _http(self) -> httpx.AsyncClient:
        """The shared client for this call, created once on first request."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=20.0, transport=self._transport)
        return self._client

    async def aclose(self) -> None:
        """Close the shared connection pool. Best-effort, called on call teardown."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        resp = await self._http().post(
            f"{self._base_url}{path}", json=body, headers=self._headers()
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data

    async def _get(self, path: str) -> dict[str, Any]:
        resp = await self._http().get(
            f"{self._base_url}{path}", headers=self._headers()
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data

    async def get_realtor(self) -> dict[str, Any]:
        """The realtor's synthesized persona (name/agency/area/tagline/tone) for the agent
        voice. Fields are null when nothing is connected yet; the agent then stays generic.
        """
        return await self._get("/api/v1/realtor")

    async def recall(self, realtor: str, criteria: str) -> str:
        """Ask the backend to recall matching listings; return the grounded answer."""
        data = await self._post(
            "/api/v1/recall", {"realtor": realtor, "criteria": criteria}
        )
        return str(data.get("answer", ""))

    async def list_listings(self) -> list[dict[str, Any]]:
        """The realtor's structured listing catalog (address/price/beds/image_url), used to
        push house cards to the caller's screen during a call.
        """
        resp = await self._http().get(
            f"{self._base_url}/api/v1/listings/catalog", headers=self._headers()
        )
        resp.raise_for_status()
        data: list[dict[str, Any]] = resp.json()
        return data

    async def capture_lead(self, buyer: dict[str, Any]) -> dict[str, Any]:
        """Upsert a buyer keyed by phone."""
        return await self._post("/api/v1/buyers", buyer)

    async def get_buyer(self, phone: str) -> dict[str, Any]:
        """Recall a returning buyer by phone (name, prior criteria, homes discussed). Returns
        {"found": bool, ...}; found is False for a new or forgotten caller. The phone is
        URL-encoded so it can never traverse or inject the request path.
        """
        return await self._get(f"/api/v1/buyers/{quote(phone, safe='')}")

    async def get_buyer_profile(self, phone: str) -> dict[str, Any]:
        """The FAST structured profile (a direct row read, not Cognee): {"found": bool,
        "name", "budget", "area", "prefs_summary"}. Read at call start so a returning
        buyer is recognized without blocking the greeting on the 10-20s graph recall.
        """
        return await self._get(f"/api/v1/buyers/{quote(phone, safe='')}/profile")

    async def check_availability(self) -> dict[str, Any]:
        """Open showing times on the realtor's calendar."""
        return await self._get("/api/v1/availability")

    async def book_showing(self, booking: dict[str, Any]) -> dict[str, Any]:
        """Book an in-person showing (idempotent by idempotency_key)."""
        return await self._post("/api/v1/bookings", booking)

    async def forget_buyer(self, phone: str) -> dict[str, Any]:
        """Forget a buyer on request (removes their Cognee dataset)."""
        resp = await self._http().delete(
            f"{self._base_url}/api/v1/buyers/{quote(phone, safe='')}",
            headers=self._headers(),
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data

    async def close_call(self, room: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist the call log and fold the conversation into permanent memory."""
        return await self._post(f"/api/v1/calls/{room}/close", payload)

    async def report_agent_state(
        self,
        room: str,
        active: str,
        action: str,
        from_agent: str | None = None,
    ) -> None:
        """Report which specialist now holds this call to the live graph. Best-effort: the
        caller (CallContext.report_state) fires this in the background and swallows failures,
        so a down backend never affects the voice turn."""
        await self._post(
            "/api/v1/agent-state",
            {"room": room, "active": active, "action": action, "from": from_agent},
        )
