from typing import Any

from pydantic import BaseModel


class BuyerUpsert(BaseModel):
    phone: str
    name: str | None = None
    email: str | None = None
    criteria: dict[str, Any] | None = None
    room_name: str | None = None


class BuyerUpsertResponse(BaseModel):
    phone: str
    name: str | None = None


class BuyerRecall(BaseModel):
    found: bool
    phone: str
    summary: str | None = None
