"""Booking orchestration: idempotency, cal.com, Showing node, operational row.

Idempotency is our-side (one Booking row per idempotency_key; the agent uses one key per
call). cal.com has no idempotency mechanism, so a booking POST is never retried; a cal
failure marks the row rejected. On an accepted booking we write a Showing node into Cognee.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.core.config import config
from src.memory.store import get_memory_store
from src.models.booking_model import Booking
from src.repository import booking_repository
from src.services import cal_service


def _parse_start(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _to_dict(row: Booking) -> dict[str, Any]:
    return {
        "id": row.id,
        "idempotency_key": row.idempotency_key,
        "status": row.status,
        "cal_uid": row.cal_uid,
        "synced": row.synced,
        "address": row.address,
    }


async def book_showing(payload: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    key = payload["idempotency_key"]

    existing = await booking_repository.get_by_idempotency_key(key)
    if existing is not None:
        return _to_dict(existing)

    row = await booking_repository.insert_pending(
        {
            "idempotency_key": key,
            "room_name": payload.get("room_name"),
            "tenant_id": tenant_id,
            "property_code": payload.get("property_code"),
            "address": payload.get("address"),
            "start_utc": _parse_start(payload.get("start")),
            "timezone": payload.get("timezone"),
            "status": "pending",
            "attendee_name": payload.get("name"),
            "phone": payload.get("phone"),
        }
    )

    api_key = config.CAL_API_KEY.get_secret_value() if config.CAL_API_KEY else None
    if not api_key or config.RR_CAL_EVENT_TYPE_ID is None:
        # cal not configured: leave the row pending (the agent offers a spoken fallback).
        return _to_dict(row)

    assert row.id is not None
    try:
        cal = await cal_service.create_showing_booking(
            event_type_id=config.RR_CAL_EVENT_TYPE_ID,
            start_utc_iso=payload["start"],
            attendee_name=payload.get("name") or "Buyer",
            attendee_phone=payload.get("phone") or "",
            attendee_timezone=payload.get("timezone") or config.CAL_DEFAULT_TIMEZONE,
            property_address=payload.get("address") or "",
            api_key=api_key,
        )
    except Exception:  # noqa: BLE001  (cal failure -> reject this row, never retry)
        updated = await booking_repository.set_result(
            row.id, cal_uid=None, status="rejected", synced=False
        )
        return _to_dict(updated)

    updated = await booking_repository.set_result(
        row.id, cal_uid=cal["uid"], status=cal["status"], synced=cal["synced"]
    )
    if cal["status"] == "accepted" and tenant_id:
        await get_memory_store().add_showing(
            tenant_id=tenant_id,
            phone=payload.get("phone"),
            property_code=payload.get("property_code"),
            address=payload.get("address"),
            when_utc=payload["start"],
        )
    return _to_dict(updated)
