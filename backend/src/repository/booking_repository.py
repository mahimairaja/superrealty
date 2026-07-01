"""Lean Booking persistence (operational row), keyed by idempotency_key.

Uses its own Database engine (lazy singleton) rather than the DI container, to keep the
booking flow self-contained. Idempotency is enforced here via the unique idempotency_key.
"""

from __future__ import annotations

from sqlmodel import col, select

from src.core.config import config
from src.core.database import Database
from src.models.booking_model import Booking

_db: Database | None = None


def _database() -> Database:
    global _db
    if _db is None:
        _db = Database(config)
    return _db


async def get_by_idempotency_key(key: str) -> Booking | None:
    async with _database().session() as session:
        result = await session.execute(
            select(Booking).where(Booking.idempotency_key == key)
        )
        return result.scalars().first()


async def insert_pending(values: dict) -> Booking:
    async with _database().session() as session:
        obj = Booking(**values)
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj


async def set_result(
    booking_id: int, *, cal_uid: str | None, status: str, synced: bool
) -> Booking:
    async with _database().session() as session:
        obj = await session.get(Booking, booking_id)
        if obj is None:
            raise ValueError(f"booking {booking_id} not found")
        obj.cal_uid = cal_uid
        obj.status = status
        obj.synced = synced
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj


async def list_recent(limit: int = 20, tenant_id: str | None = None) -> list[Booking]:
    """Recent bookings, newest first. When tenant_id is given the result is scoped to
    that tenant (the console always passes it); None returns across tenants (internal use).
    """
    async with _database().session() as session:
        stmt = select(Booking)
        if tenant_id is not None:
            stmt = stmt.where(Booking.tenant_id == tenant_id)
        stmt = stmt.order_by(col(Booking.created_at).desc()).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())
