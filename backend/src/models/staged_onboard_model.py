from typing import Any

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from src.models.base_model import BaseModel


class StagedOnboard(BaseModel, table=True):
    """The onboarding review buffer for one tenant, persisted so it survives a backend restart
    (and works across workers, removing the WEB_CONCURRENCY=1 crutch).

    One row per tenant: the reviewed-but-not-yet-live listing drafts plus the inferred realtor
    profile. Cleared on confirm (the drafts move into Cognee, the system of record) or when the
    realtor re-onboards. Intentionally not the system of record: a short-lived staging area.
    """

    __tablename__ = "staged_onboards"

    tenant_id: str = Field(index=True, unique=True, nullable=False)
    drafts: list[dict[str, Any]] = Field(
        default_factory=list, sa_column=Column(JSONB, nullable=False)
    )
    profile: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
