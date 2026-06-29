from pydantic import BaseModel


class Slot(BaseModel):
    startUtc: str
    label: str


class AvailabilityDay(BaseModel):
    date: str
    slots: list[Slot]


class AvailabilityResponse(BaseModel):
    timezone: str
    days: list[AvailabilityDay]
