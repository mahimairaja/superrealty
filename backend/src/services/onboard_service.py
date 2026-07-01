"""Onboarding: extract a realtor's own listings and stage them for review.

Listings are staged (per tenant) so the realtor can review, correct, or remove a home BEFORE
it goes live to the assistant. A confirm step inserts the corrected set into the Cognee memory
graph (the system of record). Staging is intentionally not the system of record; it is a
short-lived review buffer.

The store is persisted to Postgres in the running app (one `staged_onboards` row per tenant),
so a review survives a backend restart and works across workers (no WEB_CONCURRENCY=1 crutch).
It is exposed as a FastAPI dependency; tests override it with an in-memory implementation so the
suite needs no database.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Protocol

from fastapi import Depends
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from src.core.config import config
from src.core.database import Database
from src.models.staged_onboard_model import StagedOnboard
from src.services import extraction_service


class StagingStore(Protocol):
    async def stage(
        self, tenant_id: str, listings: list[dict[str, Any]]
    ) -> list[dict[str, Any]]: ...

    async def list(self, tenant_id: str) -> list[dict[str, Any]]: ...

    async def patch(
        self, tenant_id: str, draft_id: str, changes: dict[str, Any]
    ) -> dict[str, Any] | None: ...

    async def remove(self, tenant_id: str, draft_id: str) -> bool: ...

    async def stage_profile(
        self, tenant_id: str, profile: dict[str, Any] | None
    ) -> None: ...

    async def get_profile(self, tenant_id: str) -> dict[str, Any] | None: ...

    async def clear(self, tenant_id: str | None = None) -> None: ...


def _new_drafts(listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"id": uuid.uuid4().hex[:12], **item} for item in listings]


class InMemoryStagingStore:
    """Process-local staging. The default in tests and local dev without a database."""

    def __init__(self) -> None:
        self._by_tenant: dict[str, dict[str, dict[str, Any]]] = {}
        self._profiles: dict[str, dict[str, Any]] = {}

    async def stage(
        self, tenant_id: str, listings: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        bucket = self._by_tenant.setdefault(tenant_id, {})
        out = _new_drafts(listings)
        for draft in out:
            bucket[draft["id"]] = draft
        return out

    async def list(self, tenant_id: str) -> list[dict[str, Any]]:
        return list(self._by_tenant.get(tenant_id, {}).values())

    async def patch(
        self, tenant_id: str, draft_id: str, changes: dict[str, Any]
    ) -> dict[str, Any] | None:
        draft = self._by_tenant.get(tenant_id, {}).get(draft_id)
        if draft is None:
            return None
        draft.update({k: v for k, v in changes.items() if v is not None})
        return draft

    async def remove(self, tenant_id: str, draft_id: str) -> bool:
        return self._by_tenant.get(tenant_id, {}).pop(draft_id, None) is not None

    async def stage_profile(
        self, tenant_id: str, profile: dict[str, Any] | None
    ) -> None:
        if profile:
            self._profiles[tenant_id] = profile

    async def get_profile(self, tenant_id: str) -> dict[str, Any] | None:
        return self._profiles.get(tenant_id)

    async def clear(self, tenant_id: str | None = None) -> None:
        if tenant_id is None:
            self._by_tenant.clear()
            self._profiles.clear()
        else:
            self._by_tenant.pop(tenant_id, None)
            self._profiles.pop(tenant_id, None)


_db: Database | None = None


def _database() -> Database:
    global _db
    if _db is None:
        _db = Database(config)
    return _db


class DbStagingStore:
    """Postgres-backed staging: one `staged_onboards` row per tenant. Read-modify-write on a
    small per-tenant row (short-lived, reviewed by a single realtor), so no row locking."""

    async def _row(self, session: AsyncSession, tenant_id: str) -> StagedOnboard | None:
        result = await session.execute(
            select(StagedOnboard).where(col(StagedOnboard.tenant_id) == tenant_id)
        )
        return result.scalars().first()

    async def stage(
        self, tenant_id: str, listings: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        out = _new_drafts(listings)
        try:
            await self._append_or_create(tenant_id, out)
        except IntegrityError:
            # Lost a concurrent insert race (tenant_id is unique): the row now exists, so the
            # retry takes the append path instead of 500ing.
            await self._append_or_create(tenant_id, out)
        return out

    async def _append_or_create(
        self, tenant_id: str, new_drafts: list[dict[str, Any]]
    ) -> None:
        async with _database().session() as session:
            row = await self._row(session, tenant_id)
            if row is None:
                row = StagedOnboard(
                    tenant_id=tenant_id, drafts=new_drafts, profile=None
                )
            else:
                row.drafts = [
                    *row.drafts,
                    *new_drafts,
                ]  # reassign so JSONB change tracks
            session.add(row)
            await session.commit()

    async def list(self, tenant_id: str) -> list[dict[str, Any]]:
        async with _database().session() as session:
            row = await self._row(session, tenant_id)
            return list(row.drafts) if row else []

    async def patch(
        self, tenant_id: str, draft_id: str, changes: dict[str, Any]
    ) -> dict[str, Any] | None:
        clean = {k: v for k, v in changes.items() if v is not None}
        async with _database().session() as session:
            row = await self._row(session, tenant_id)
            if row is None:
                return None
            drafts = list(row.drafts)
            updated: dict[str, Any] | None = None
            for i, draft in enumerate(drafts):
                if draft.get("id") == draft_id:
                    updated = {**draft, **clean}
                    drafts[i] = updated
                    break
            if updated is None:
                return None
            row.drafts = drafts
            session.add(row)
            await session.commit()
            return updated

    async def remove(self, tenant_id: str, draft_id: str) -> bool:
        async with _database().session() as session:
            row = await self._row(session, tenant_id)
            if row is None:
                return False
            drafts = [d for d in row.drafts if d.get("id") != draft_id]
            if len(drafts) == len(row.drafts):
                return False
            row.drafts = drafts
            session.add(row)
            await session.commit()
            return True

    async def stage_profile(
        self, tenant_id: str, profile: dict[str, Any] | None
    ) -> None:
        if not profile:
            return
        try:
            await self._set_profile(tenant_id, profile)
        except IntegrityError:
            await self._set_profile(
                tenant_id, profile
            )  # lost the insert race; row exists now

    async def _set_profile(self, tenant_id: str, profile: dict[str, Any]) -> None:
        async with _database().session() as session:
            row = await self._row(session, tenant_id)
            if row is None:
                row = StagedOnboard(tenant_id=tenant_id, drafts=[], profile=profile)
            else:
                row.profile = profile
            session.add(row)
            await session.commit()

    async def get_profile(self, tenant_id: str) -> dict[str, Any] | None:
        async with _database().session() as session:
            row = await self._row(session, tenant_id)
            return row.profile if row else None

    async def clear(self, tenant_id: str | None = None) -> None:
        async with _database().session() as session:
            stmt = delete(StagedOnboard)
            if tenant_id is not None:
                stmt = stmt.where(col(StagedOnboard.tenant_id) == tenant_id)
            await session.execute(stmt)
            await session.commit()


_store: StagingStore | None = None


def get_staging_store() -> StagingStore:
    """FastAPI dependency: the DB-backed staging store in the running app. Tests override this
    dependency with an InMemoryStagingStore, so the suite needs no database."""
    global _store
    if _store is None:
        _store = DbStagingStore()
    return _store


StagedStore = Annotated[StagingStore, Depends(get_staging_store)]


def extract_drafts(content: bytes, filename: str | None) -> list[dict[str, Any]]:
    """Pick the extractor by file type. HTML and PDF fall back to the LLM path only when
    an extractor is given one; the structured paths need no network.
    """
    name = (filename or "").lower()
    if name.endswith(".csv"):
        return extraction_service.extract_from_csv(content)
    if name.endswith(".pdf"):
        return extraction_service.extract_from_pdf(content)
    text = content.decode("utf-8", errors="replace")
    return extraction_service.extract_from_html(text)
