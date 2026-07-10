"""The Property specialist: search and describe homes from the realtor's connected listings."""

from __future__ import annotations

import logging
from typing import Any

from livekit.agents import Agent, RunContext, function_tool

from src.agents.base_agent import RealtyBaseAgent
from src.agents.call_context import PROPERTY, CallContext
from src.agents.listing_filters import (
    ListingSearchFilters,
    filter_listings,
    summarize_filters,
)
from src.core.tool_tracing import traced_tool
from src.prompts.instructions import property_instructions

logger = logging.getLogger("agent")


def _find_listing(catalog: list[dict[str, Any]], home: str) -> dict[str, Any] | None:
    """Resolve a home the buyer names (by code or address substring) to a catalog entry."""
    needle = home.strip().lower()
    for h in catalog:
        if needle and needle == str(h.get("code") or "").lower():
            return h
    for h in catalog:
        if needle and needle in str(h.get("address") or "").lower():
            return h
    return None


def _format_listings_answer(matches: list[dict[str, Any]], total: int) -> str:
    """Turn the realtor's real catalog rows into one grounded, speakable answer."""
    if not matches:
        return (
            "I don't have a connected listing that fits that just now. I can take your "
            "details and follow up as soon as something matches."
        )

    def _price(h: dict[str, Any]) -> str:
        p = h.get("price")
        return f"${int(p):,}" if isinstance(p, int | float) else "price on request"

    shown = matches[:6]
    parts = []
    for h in shown:
        beds = h.get("beds")
        bed_txt = f", {beds} bed" if beds else ""
        parts.append(f"{h.get('address') or 'a home'} at {_price(h)}{bed_txt}")
    listing_text = "; ".join(parts)
    count = len(matches)
    if count >= total:
        head = (
            "I have one listing right now" if count == 1 else f"I have {count} listings"
        )
    else:
        head = "I found one that fits" if count == 1 else f"I found {count} that fit"
    tail = (
        f" I've put all {count} on your screen. Which would you like to hear more about?"
        if count > len(shown)
        else ""
    )
    return f"{head}: {listing_text}.{tail}"


class PropertyAgent(RealtyBaseAgent):
    ID = PROPERTY
    ACTION = "Searching listings"

    def __init__(self, ctx: CallContext) -> None:
        super().__init__(ctx, instructions=property_instructions(ctx.persona or None))

    async def _listings_answer(self, filters: ListingSearchFilters) -> str:
        catalog = await self.ctx.ensure_catalog()
        if not catalog:
            return (
                "I'm having a little trouble pulling up listings right now. Can I take "
                "your details and follow up?"
            )
        matches = filter_listings(catalog, filters)
        answer = _format_listings_answer(matches, len(catalog))
        echo = summarize_filters(filters)
        return f"{echo[0].upper()}{echo[1:]}: {answer}" if echo else answer

    @function_tool
    @traced_tool
    async def search_listings(
        self,
        context: RunContext,
        min_beds: int | None = None,
        min_baths: float | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        area: str | None = None,
        min_sqft: int | None = None,
        max_sqft: int | None = None,
        sort_by: str | None = None,
        sort_order: str | None = None,
    ) -> str:
        """Find homes from the realtor's own connected listings, and always call this
        before naming any home. Fill only the fields the buyer stated: min_beds,
        min_baths, min_price and max_price in dollars, area (a neighbourhood or city),
        min_sqft and max_sqft. Leave every field blank to list all current listings
        rather than asking for criteria first. Optionally sort_by one of "price",
        "beds", or "sqft" with sort_order "asc" or "desc".
        """
        filters = ListingSearchFilters(
            min_beds=min_beds,
            min_baths=min_baths,
            min_price=min_price,
            max_price=max_price,
            area=area,
            min_sqft=min_sqft,
            max_sqft=max_sqft,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        answer = await self._listings_answer(filters)
        self.ctx.fire(self.ctx.emit_shortlist(filters))
        return answer

    @function_tool
    @traced_tool
    async def show_home(self, context: RunContext, home: str) -> str:
        """Pull ONE specific home up on the buyer's screen with its photo and full details.
        Call this whenever the buyer asks about a particular home or you are describing one in
        depth. `home` is the address or the listing code (e.g. "88 Maple Ridge" or "RR-102").
        """
        listing = _find_listing(await self.ctx.ensure_catalog(), home)
        if not listing:
            return "I couldn't find that exact home. Want me to list what's available?"
        self.ctx.fire(self.ctx.push_event("property", listing))
        beds = listing.get("beds")
        price = listing.get("price")
        price_txt = (
            f"${int(price):,}" if isinstance(price, int | float) else "price on request"
        )
        return (
            f"Putting {listing.get('address')} on your screen now: {price_txt}"
            f"{f', {beds} bed' if beds else ''}. {listing.get('description') or ''}"
        )

    @function_tool
    async def to_scheduling(self, context: RunContext) -> Agent:
        """Hand the call to the scheduling specialist when the buyer wants showing times or to
        book a visit."""
        from src.agents.scheduling_agent import SchedulingAgent

        return self._handoff(SchedulingAgent(self.ctx))

    @function_tool
    async def to_concierge(self, context: RunContext) -> Agent:
        """Hand the call back to the concierge when the buyer is done looking at homes."""
        from src.agents.concierge_agent import ConciergeAgent

        return self._handoff(ConciergeAgent(self.ctx))
