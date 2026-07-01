"""LLM extraction: turn cleaned page content into structured listings and a realtor profile.

This is the "clean content -> structured output" step every URL-to-data tool uses. We give
the model a strict JSON schema so it fills exactly our fields; unset fields come back null
rather than invented (the realtor reviews everything before it goes live either way).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_MODEL = "gpt-4.1-mini"
_MAX_INPUT_CHARS = 16000  # keep prompts bounded / cheap
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI | None:
    global _client
    if _client is None:
        key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not key:
            return None
        # Bound each call so a single hung/retrying request can't eat the onboard deadline.
        _client = AsyncOpenAI(api_key=key, timeout=20.0, max_retries=1)
    return _client


_LISTING_ITEM = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "code": {"type": ["string", "null"]},
        "address": {"type": ["string", "null"]},
        "price": {"type": ["number", "null"]},
        "beds": {"type": ["integer", "null"]},
        "baths": {"type": ["number", "null"]},
        "sqft": {"type": ["integer", "null"]},
        "description": {"type": ["string", "null"]},
        "image_url": {"type": ["string", "null"]},
        "area": {"type": ["string", "null"]},
    },
    "required": [
        "code",
        "address",
        "price",
        "beds",
        "baths",
        "sqft",
        "description",
        "image_url",
        "area",
    ],
}

_LISTINGS_SCHEMA = {
    "name": "listings",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {"listings": {"type": "array", "items": _LISTING_ITEM}},
        "required": ["listings"],
    },
}

_PROFILE_SCHEMA = {
    "name": "realtor_profile",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": ["string", "null"]},
            "agency": {"type": ["string", "null"]},
            "area": {"type": ["string", "null"]},
            "tagline": {"type": ["string", "null"]},
            "tone": {"type": ["string", "null"]},
        },
        "required": ["name", "agency", "area", "tagline", "tone"],
    },
}


async def _structured(text: str, schema: dict[str, Any], instruction: str) -> Any:
    client = _get_client()
    if client is None or not text.strip():
        return None
    if len(text) > _MAX_INPUT_CHARS:
        logger.warning(
            "LLM input truncated %d->%d chars; content past the cutoff (e.g. trailing "
            "listings) is dropped",
            len(text),
            _MAX_INPUT_CHARS,
        )
    try:
        # The dynamic dict messages/response_format are runtime-correct but don't match
        # openai's heavily-overloaded TypedDict signatures under a strict checker.
        resp = await client.chat.completions.create(  # type: ignore[call-overload]
            model=_MODEL,
            messages=[
                {"role": "system", "content": instruction},
                {"role": "user", "content": text[:_MAX_INPUT_CHARS]},
            ],
            response_format={"type": "json_schema", "json_schema": schema},
            temperature=0,
        )
        content = resp.choices[0].message.content
        return json.loads(content) if content else None
    except Exception as exc:  # noqa: BLE001  (LLM is best-effort; caller degrades)
        logger.warning("LLM structured call failed: %s", exc)
        return None


async def extract_listings(text: str) -> list[dict[str, Any]]:
    """Pull every real-estate listing out of a page's cleaned text/markdown. Only extract what
    is actually on the page; never invent a home, price, or detail.
    """
    data = await _structured(
        text,
        _LISTINGS_SCHEMA,
        "You extract real-estate listings from a realtor's own web page. Return every "
        "distinct property you can find. Use only facts present in the text; if a field is "
        "not stated, return null. Never invent a home, address, price, or detail.",
    )
    if not isinstance(data, dict):
        return []
    items = data.get("listings")
    return (
        [i for i in items if isinstance(i, dict) and i.get("address")] if items else []
    )


async def synthesize_profile(text: str) -> dict[str, Any] | None:
    """Summarize who the realtor is (for the assistant's persona) from their site's own text.
    All fields null when unknown; the realtor confirms before anything goes live.
    """
    data = await _structured(
        text,
        _PROFILE_SCHEMA,
        "You summarize a solo real-estate agent from their own website text into a short "
        "profile: their name, agency/brokerage, the area they serve, a one-line tagline, and "
        "their tone of voice (a few words). Use only what the text supports; null if unknown.",
    )
    return data if isinstance(data, dict) else None
