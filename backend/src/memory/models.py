"""Cognee data models for the realty memory graph.

Realtor represents Listing, Listing located_in Neighbourhood, Buyer interested_in Listing,
Showing for a Buyer and a Listing. Edge fields use SkipValidation so a node can reference
other DataPoints without pydantic recursing into them (Cognee's documented pattern).
index_fields mark the text Cognee makes searchable.
"""

from __future__ import annotations

from typing import Any

from cognee.infrastructure.engine import DataPoint
from pydantic import SkipValidation


class Neighbourhood(DataPoint):
    name: str
    city: str | None = None
    metadata: dict[str, Any] = {"index_fields": ["name"]}


class Listing(DataPoint):
    code: str
    address: str
    price: float | None = None
    beds: int | None = None
    baths: float | None = None
    sqft: int | None = None
    description: str | None = None
    image_url: str | None = None
    located_in: SkipValidation[Any] = None
    metadata: dict[str, Any] = {"index_fields": ["address", "description"]}


class Realtor(DataPoint):
    name: str
    email: str | None = None
    # Persona inferred from the realtor's own site during URL onboarding; drives how the live
    # voice agent introduces itself and speaks. All optional (a file/CSV onboard sets none).
    agency: str | None = None
    area: str | None = None
    tagline: str | None = None
    tone: str | None = None
    represents: SkipValidation[Any] = None
    metadata: dict[str, Any] = {"index_fields": ["name"]}


class Buyer(DataPoint):
    phone: str
    name: str | None = None
    email: str | None = None
    criteria: dict[str, Any] | None = None
    interested_in: SkipValidation[Any] = None
    # The neighbourhood the buyer is looking in (from their criteria area). Linking here attaches
    # the buyer to the same Neighbourhood node the realtor's listings sit in, so the graph is one
    # connected structure (Buyer -> Neighbourhood <- Listing <- Realtor) rather than loose buyers.
    wants_in: SkipValidation[Any] = None
    metadata: dict[str, Any] = {"index_fields": ["name", "phone"]}


class Showing(DataPoint):
    when_utc: str
    buyer: SkipValidation[Any] = None
    listing: SkipValidation[Any] = None
    metadata: dict[str, Any] = {"index_fields": []}
