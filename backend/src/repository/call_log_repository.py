"""Lean CallLog persistence (operational row). Uses its own Database engine, like the
booking repository, to keep the call-close path self-contained."""

from __future__ import annotations

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
