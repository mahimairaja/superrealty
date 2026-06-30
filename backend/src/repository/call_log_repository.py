"""Lean CallLog persistence (operational row). Uses its own Database engine, like the
booking repository, to keep the call-close path self-contained."""

from __future__ import annotations

from sqlmodel import col, select

from src.core.config import config
from src.core.database import Database
from src.models.call_log_model import CallLog

_db: Database | None = None


def _database() -> Database:
    global _db
    if _db is None:
        _db = Database(config)
    return _db


async def create(values: dict) -> CallLog:
    async with _database().session() as session:
        obj = CallLog(**values)
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj


async def list_recent(
    limit: int = 20, tenant_id: str | None = None
) -> list[CallLog]:
    """Recent call logs, newest first. When tenant_id is given the result is scoped to
    that tenant (the console always passes it); None returns across tenants (internal use).
    """
    async with _database().session() as session:
        stmt = select(CallLog)
        if tenant_id is not None:
            stmt = stmt.where(CallLog.tenant_id == tenant_id)
        stmt = stmt.order_by(col(CallLog.created_at).desc()).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())
