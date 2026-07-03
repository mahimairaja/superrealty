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


class ListingCreate(BaseModel):
    """A single home the realtor adds by hand from the console, straight to their live catalog.

    Only the address is required; everything else is optional. Area drives which neighbourhood
    the home joins (and so which waiting buyers it can match). A code is generated if omitted.
    """

    address: str
    code: str | None = None
    price: float | None = None
    beds: int | None = None
    baths: float | None = None
    sqft: int | None = None
    description: str | None = None
    area: str | None = None
    image_url: str | None = None


class RealtorProfile(BaseModel):
    """What we inferred about the realtor from their site (for the assistant's persona).
    Every field is optional; the realtor confirms before anything goes live.
    """

    name: str | None = None
    agency: str | None = None
    area: str | None = None
    tagline: str | None = None
    tone: str | None = None


class OnboardResponse(BaseModel):
    realtor: str
    listings: list[ListingDraft]
    profile: RealtorProfile | None = None


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


class LiveListing(BaseModel):
    """A connected listing read back from Cognee for the realtor's dashboard (post-confirm)."""

    code: str | None = None
    address: str | None = None
    price: float | None = None
    beds: int | None = None
    baths: float | None = None
    sqft: int | None = None
    description: str | None = None
    image_url: str | None = None
