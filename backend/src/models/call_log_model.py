from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from src.models.base_model import BaseModel


class CallLog(BaseModel, table=True):
    """Operational record of a call. The buyer and listings discussed live in Cognee;
    this row keeps the transcript and outcome, with a soft link to a Booking row.
    """

    __tablename__ = "call_logs"

    tenant_id: str | None = Field(default=None, index=True)
    room_name: str = Field(index=True, nullable=False)
    agent_name: str | None = Field(default=None)
    started_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    ended_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    duration_seconds: int | None = Field(default=None)
    outcome: str | None = Field(default=None)
    buyer_phone: str | None = Field(default=None, index=True)
    booking_id: int | None = Field(
        default=None,
        sa_column=Column(
            Integer, ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True
        ),
    )
    transcript: list[dict[str, Any]] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
