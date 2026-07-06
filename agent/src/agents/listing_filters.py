"""Typed, validated listing-search filters for the voice agent.

The search tool used to take a free-text ``criteria`` string and regex a bedroom
count out of it. This replaces that with a small validated schema so matching is
deterministic and unit-testable, and so a bad LLM-extracted value degrades quietly
(a warning) instead of failing a live call. Fields mirror the realtor's REAL
catalog rows (code/address/price/beds/baths/sqft/area); there is no property_type
or amenities data, so there are no filters for them.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, field_validator, model_validator

logger = logging.getLogger("agent")

_SORT_FIELDS = {"price", "beds", "sqft"}
_SORT_ORDERS = {"asc", "desc"}


class ListingSearchFilters(BaseModel):
    """What the buyer asked for, extracted into typed fields. Every field is optional;
    an all-empty filter means "list everything". Validators never raise: an unknown
    sort or an inverted range is logged and dropped so a call is never broken by one
    bad value."""

    min_beds: int | None = None
    min_baths: float | None = None
    min_price: float | None = None
    max_price: float | None = None
    area: str | None = None
    min_sqft: int | None = None
    max_sqft: int | None = None
    sort_by: str | None = None
    sort_order: str | None = None

    @field_validator("sort_by")
    @classmethod
    def _whitelist_sort_by(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip().lower()
        if v not in _SORT_FIELDS:
            logger.warning("listing filter: ignoring unknown sort_by=%r", v)
            return None
        return v

    @field_validator("sort_order")
    @classmethod
    def _whitelist_sort_order(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = str(v).strip().lower()
        if v not in _SORT_ORDERS:
            logger.warning("listing filter: ignoring unknown sort_order=%r", v)
            return None
        return v

    @field_validator("area")
    @classmethod
    def _empty_area_to_none(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return str(v).strip() or None

    @model_validator(mode="after")
    def _sane(self) -> ListingSearchFilters:
        if (
            self.min_price is not None
            and self.max_price is not None
            and self.min_price > self.max_price
        ):
            logger.warning(
                "listing filter: inverted price range (min=%s > max=%s); ignoring both",
                self.min_price,
                self.max_price,
            )
            self.min_price = self.max_price = None
        if (
            self.min_sqft is not None
            and self.max_sqft is not None
            and self.min_sqft > self.max_sqft
        ):
            logger.warning(
                "listing filter: inverted sqft range (min=%s > max=%s); ignoring both",
                self.min_sqft,
                self.max_sqft,
            )
            self.min_sqft = self.max_sqft = None
        # A sort order with nothing to sort by is meaningless.
        if self.sort_order is not None and self.sort_by is None:
            self.sort_order = None
        return self

    def is_empty(self) -> bool:
        """True when no field is set (a "list everything" request)."""
        return not any(
            v is not None for v in self.model_dump(exclude={"sort_order"}).values()
        )


def filter_listings(
    catalog: list[dict[str, Any]], f: ListingSearchFilters
) -> list[dict[str, Any]]:
    """Deterministically narrow (and optionally sort) the catalog by the filters.

    A home with an unknown value for a bounded field (e.g. no price when a budget is
    set) is excluded, so the assistant never claims a home fits a criterion we cannot
    confirm. An all-empty filter returns the whole catalog.
    """

    def ok(h: dict[str, Any]) -> bool:
        if f.min_beds is not None and (h.get("beds") or 0) < f.min_beds:
            return False
        if f.min_baths is not None and (h.get("baths") or 0) < f.min_baths:
            return False
        price = h.get("price")
        if f.min_price is not None and (price is None or price < f.min_price):
            return False
        if f.max_price is not None and (price is None or price > f.max_price):
            return False
        if f.min_sqft is not None and (h.get("sqft") or 0) < f.min_sqft:
            return False
        sqft = h.get("sqft")
        if f.max_sqft is not None and (sqft is None or sqft > f.max_sqft):
            return False
        if f.area:
            needle = f.area.lower()
            area = str(h.get("area") or "").lower()
            addr = str(h.get("address") or "").lower()
            if needle not in area and needle not in addr:
                return False
        return True

    matches = [h for h in catalog if ok(h)]
    if f.sort_by:
        sort_key: str = f.sort_by
        known = [h for h in matches if h.get(sort_key) is not None]
        unknown = [h for h in matches if h.get(sort_key) is None]
        # known rows all have a present, non-None sort value, so h[sort_key] is safe.
        known.sort(key=lambda h: h[sort_key], reverse=f.sort_order == "desc")
        # Homes with an unknown value for the sort field always trail the ranked ones.
        matches = known + unknown
    return matches


def summarize_filters(f: ListingSearchFilters) -> str:
    """A short human phrase of the active filters for the assistant to confirm back,
    e.g. "in Sarnia, 3+ beds, under $480,000". Empty string when nothing is set."""
    parts: list[str] = []
    if f.area:
        parts.append(f"in {f.area}")
    if f.min_beds:
        parts.append(f"{f.min_beds}+ beds")
    if f.min_baths:
        parts.append(f"{f.min_baths:g}+ baths")
    if f.min_price is not None and f.max_price is not None:
        parts.append(f"${int(f.min_price):,}-${int(f.max_price):,}")
    elif f.max_price is not None:
        parts.append(f"under ${int(f.max_price):,}")
    elif f.min_price is not None:
        parts.append(f"over ${int(f.min_price):,}")
    if f.min_sqft:
        parts.append(f"{f.min_sqft:,}+ sqft")
    return ", ".join(parts)
