from datetime import datetime
from typing import Any

from pydantic import BaseModel


class CallClose(BaseModel):
    agent_name: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    outcome: str | None = None
    buyer_phone: str | None = None
    booking_id: int | None = None
    transcript: list[dict[str, Any]] | None = None


class CallCloseResponse(BaseModel):
    id: int | None = None
    room_name: str
