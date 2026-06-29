from pydantic import BaseModel


class ListingDraft(BaseModel):
    """A parsed listing staged for the realtor to review before it goes live to Cognee."""

    id: str
    code: str | None = None
    address: str
    price: float | None = None
    beds: int | None = None
    baths: float | None = None
    sqft: int | None = None
    description: str | None = None
    image_url: str | None = None
    area: str | None = None


class OnboardResponse(BaseModel):
    realtor: str
    listings: list[ListingDraft]


class ListingPatch(BaseModel):
    code: str | None = None
    address: str | None = None
    price: float | None = None
    beds: int | None = None
    baths: float | None = None
    sqft: int | None = None
    description: str | None = None
    image_url: str | None = None
    area: str | None = None


class ConfirmResponse(BaseModel):
    realtor: str
    inserted: int
