from pydantic import BaseModel


class MatchRequest(BaseModel):
    area: str | None = None
    beds: int | None = None
    price: float | None = None
    address: str | None = None


class MatchResponse(BaseModel):
    matched: bool
    summary: str
