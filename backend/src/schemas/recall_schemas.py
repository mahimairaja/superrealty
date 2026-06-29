from typing import Any

from pydantic import BaseModel


class RecallRequest(BaseModel):
    realtor: str
    # Either a structured criteria object (area, maxPrice, minBeds, ...) or free text.
    criteria: dict[str, Any] | str
    top_k: int = 5


class RecallResponse(BaseModel):
    realtor: str
    answer: str
    match_count: int
