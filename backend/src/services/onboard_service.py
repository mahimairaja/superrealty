"""Onboarding: extract a realtor's own listings and stage them for review.

Listings are staged (in-process, per realtor) so the realtor can review, correct, or
remove a home BEFORE it goes live to the assistant. A confirm step inserts the corrected
set into the Cognee memory graph (the system of record). Staging is intentionally not the
system of record; it is a short-lived review buffer for the single-realtor M0 demo.
"""

from __future__ import annotations

import uuid
from typing import Any

from src.services import extraction_service


class StagingStore:
    def __init__(self) -> None:
        self._by_realtor: dict[str, dict[str, dict[str, Any]]] = {}
        # Inferred realtor profile per tenant (from a URL onboard), shown on review and used
        # to name the Realtor node on confirm.
        self._profiles: dict[str, dict[str, Any]] = {}

    def stage(
        self, realtor: str, listings: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        bucket = self._by_realtor.setdefault(realtor, {})
        out: list[dict[str, Any]] = []
        for item in listings:
            draft_id = uuid.uuid4().hex[:12]
            draft = {"id": draft_id, **item}
            bucket[draft_id] = draft
            out.append(draft)
        return out

    def list(self, realtor: str) -> list[dict[str, Any]]:
        return list(self._by_realtor.get(realtor, {}).values())

    def patch(
        self, realtor: str, draft_id: str, changes: dict[str, Any]
    ) -> dict[str, Any] | None:
        draft = self._by_realtor.get(realtor, {}).get(draft_id)
        if draft is None:
            return None
        draft.update({k: v for k, v in changes.items() if v is not None})
        return draft

    def remove(self, realtor: str, draft_id: str) -> bool:
        return self._by_realtor.get(realtor, {}).pop(draft_id, None) is not None

    def stage_profile(self, realtor: str, profile: dict[str, Any] | None) -> None:
        if profile:
            self._profiles[realtor] = profile

    def get_profile(self, realtor: str) -> dict[str, Any] | None:
        return self._profiles.get(realtor)

    def clear(self, realtor: str | None = None) -> None:
        if realtor is None:
            self._by_realtor.clear()
            self._profiles.clear()
        else:
            self._by_realtor.pop(realtor, None)
            self._profiles.pop(realtor, None)


_staging: StagingStore | None = None


def get_staging_store() -> StagingStore:
    global _staging
    if _staging is None:
        _staging = StagingStore()
    return _staging


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
