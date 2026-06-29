"""Async cal.com v2 client: availability (slots) and showing bookings.

The agent never calls cal.com; the backend does, on the agent's behalf. No idempotency
header is sent (cal.com v2 has none); idempotency is enforced our-side via the
bookings.idempotency_key column, and a booking POST is never retried. The optional
transport makes the client testable with httpx.MockTransport (no network, no real booking).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx

CAL_BASE_URL = "https://api.cal.com/v2"
# Version-pinned; omitting these silently routes to an older, incompatible handler.
CAL_API_VERSION_BOOKINGS = "2024-08-13"
CAL_API_VERSION_SLOTS = "2024-09-04"


async def get_available_slots(
    *,
    event_type_id: int,
    api_key: str,
    timezone: str,
    days_ahead: int = 7,
    max_per_day: int = 8,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[dict[str, Any]]:
    """Open slots for the event type, grouped by day, in the given timezone."""
    start = date.today()
    end = start + timedelta(days=days_ahead)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "cal-api-version": CAL_API_VERSION_SLOTS,
    }
    params: dict[str, str | int] = {
        "eventTypeId": event_type_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timeZone": timezone,
    }
    async with httpx.AsyncClient(timeout=20.0, transport=transport) as client:
        resp = await client.get(f"{CAL_BASE_URL}/slots", headers=headers, params=params)
        resp.raise_for_status()
        raw = resp.json()["data"]

    tz = ZoneInfo(timezone)
    days: list[dict[str, Any]] = []
    for day_str in sorted(raw.keys()):
        slots = []
        for entry in raw[day_str][:max_per_day]:
            dt = datetime.fromisoformat(entry["start"])
            slots.append(
                {
                    "startUtc": dt.astimezone(ZoneInfo("UTC")).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    "label": dt.astimezone(tz).strftime("%-I:%M %p"),
                }
            )
        if slots:
            days.append({"date": day_str, "slots": slots})
    return days


async def create_showing_booking(
    *,
    event_type_id: int,
    start_utc_iso: str,
    attendee_name: str,
    attendee_phone: str,
    attendee_timezone: str,
    property_address: str,
    api_key: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    """Create a property-showing booking (books by phone). Returns confirmation fields."""
    payload = {
        "eventTypeId": event_type_id,
        "start": start_utc_iso,
        "attendee": {
            "name": attendee_name,
            "phoneNumber": attendee_phone,
            "timeZone": attendee_timezone,
            "language": "en",
        },
        "bookingFieldsResponses": {
            "property-address": property_address,
            "notes": f"Property showing for {property_address}",
        },
        "metadata": {"source": "realtyrecall"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "cal-api-version": CAL_API_VERSION_BOOKINGS,
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=20.0, transport=transport) as client:
        resp = await client.post(
            f"{CAL_BASE_URL}/bookings", headers=headers, json=payload
        )
        resp.raise_for_status()
        data = resp.json()["data"]
    return {
        "uid": data["uid"],
        "status": data["status"],
        "start": data["start"],
        "end": data.get("end"),
        "synced": bool(data.get("references")),
    }
