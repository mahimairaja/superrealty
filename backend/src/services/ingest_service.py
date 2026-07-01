"""Turn a seed URL into staged listings + a realtor profile (the fan-out onboarding engine).

Crawl the realtor's own site (fetch_service), extract listings from each page structure-first
(cheap JSON-LD/OpenGraph/DOM) and fall back to the LLM only where it pays off, dedupe, and
synthesize a short realtor profile for the assistant's persona. Nothing goes live here; the
realtor reviews and confirms everything downstream.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from src.services import extraction_service, fetch_service, llm_service

# Cap LLM extraction calls so a big site can't run up cost; structured pages don't count.
_MAX_LLM_PAGES = 8
_PROFILE_PAGES = 4
_PRICE = re.compile(r"\$\s?\d")


def _looks_like_listing(text: str) -> bool:
    """A cheap gate before spending an LLM call: a price plus a bed/bath/size word."""
    lowered = text.lower()
    return bool(_PRICE.search(text)) and any(
        k in lowered for k in ("bed", "bath", "sqft", "sq ft", "square f")
    )


def _dedupe(listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for listing in listings:
        key = (
            str(listing.get("code") or "").strip().lower()
            or str(listing.get("address") or "").strip().lower()
        )
        if key and key not in seen:
            seen.add(key)
            out.append(listing)
    return out


async def ingest_url(
    seed_url: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Crawl the seed's site and return (deduped listings, realtor profile-or-None)."""
    pages = await fetch_service.crawl(seed_url)

    listings: list[dict[str, Any]] = []
    llm_texts: list[str] = []
    for page in pages:
        if page.is_markdown:
            llm_texts.append(page.content)
            continue
        structured = extraction_service.extract_from_html(page.content)
        text = extraction_service.page_text(page.content)
        # Each structured extractor returns a single record, so an index page advertising
        # several prices collapses to one: treat that as under-extraction and prefer the
        # whole-page LLM read, which pulls out every card.
        multi_listing = len(_PRICE.findall(text)) > 1
        if structured and not (len(structured) < 2 and multi_listing):
            listings.extend(structured)
            continue
        if multi_listing or _looks_like_listing(text):
            llm_texts.append(text)
        elif structured:
            # Keep the single record: no multi-listing signal, nothing better available.
            listings.extend(structured)

    llm_texts = llm_texts[:_MAX_LLM_PAGES]  # cap cost regardless of site size
    profile_text = "\n\n".join(
        page.content if page.is_markdown else extraction_service.page_text(page.content)
        for page in pages[:_PROFILE_PAGES]
    )

    # The LLM calls are independent, so run them (and the profile) concurrently: onboarding
    # finishes in ~one round-trip of wall time instead of nine, staying inside the deadline.
    extracted_lists, profile = await asyncio.gather(
        asyncio.gather(*(llm_service.extract_listings(t) for t in llm_texts)),
        llm_service.synthesize_profile(profile_text),
    )
    for extracted in extracted_lists:
        listings.extend(extracted)

    return _dedupe(listings), profile
