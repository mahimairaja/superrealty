"""Listing extraction ladder for a realtor's OWN page or uploaded file.

The realtor connects their own listings by URL or file. We try structured data first
(JSON-LD schema.org), then OpenGraph, then DOM heuristics, then an LLM-to-fixed-JSON
backstop, and we also parse uploaded CSV and PDF. Output is a list of normalized listing
dicts. Nothing here scrapes third-party portals.
"""

from __future__ import annotations

import csv
import io
import json
import re
from collections.abc import Callable
from typing import Any

from selectolax.parser import HTMLParser

# A normalized listing dict has: code, address, price, beds, baths, sqft, description,
# image_url, area. address is the only field we require to keep a record.
LLMExtractor = Callable[[str], list[dict[str, Any]]]

_LISTING_TYPES = {
    "realestatelisting",
    "singlefamilyresidence",
    "residence",
    "house",
    "apartment",
    "product",
    "offer",
    "place",
}


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, dict | list):
        return None
    if isinstance(value, int | float):
        return float(value)
    digits = re.sub(r"[^\d.]", "", str(value))
    try:
        return float(digits) if digits else None
    except ValueError:
        return None


def _to_int(value: Any) -> int | None:
    f = _to_float(value)
    return int(f) if f is not None else None


def _norm(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": record.get("code"),
        "address": record.get("address"),
        "price": _to_float(record.get("price")),
        "beds": _to_int(record.get("beds")),
        "baths": _to_float(record.get("baths")),
        "sqft": _to_int(record.get("sqft")),
        "description": record.get("description"),
        "image_url": record.get("image_url"),
        "area": record.get("area"),
    }


def _first_image(image: Any) -> str | None:
    if isinstance(image, str):
        return image
    if isinstance(image, list) and image:
        first = image[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return first.get("url")
    if isinstance(image, dict):
        return image.get("url")
    return None


def _iter_jsonld_objects(data: Any) -> Any:
    if isinstance(data, list):
        for item in data:
            yield from _iter_jsonld_objects(item)
    elif isinstance(data, dict):
        if "@graph" in data:
            yield from _iter_jsonld_objects(data["@graph"])
        else:
            yield data


def _type_matches(obj: dict[str, Any]) -> bool:
    raw = obj.get("@type")
    types = raw if isinstance(raw, list) else [raw]
    return any(isinstance(x, str) and x.lower() in _LISTING_TYPES for x in types)


def _from_jsonld(tree: HTMLParser) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for node in tree.css('script[type="application/ld+json"]'):
        raw = node.text(deep=True, strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        for obj in _iter_jsonld_objects(data):
            if not isinstance(obj, dict) or not _type_matches(obj):
                continue
            addr = obj.get("address")
            area = addr.get("addressLocality") if isinstance(addr, dict) else None
            if isinstance(addr, dict):
                parts = [
                    addr.get(k)
                    for k in ("streetAddress", "addressLocality", "addressRegion")
                ]
                addr = ", ".join(p for p in parts if p)
            offers = obj.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            floor = obj.get("floorSize")
            rec = {
                "code": obj.get("sku") or obj.get("identifier") or obj.get("mlsNumber"),
                "address": addr or obj.get("name"),
                "price": offers.get("price") if isinstance(offers, dict) else None,
                "beds": obj.get("numberOfBedrooms") or obj.get("numberOfRooms"),
                "baths": obj.get("numberOfBathroomsTotal")
                or obj.get("numberOfBathrooms"),
                "sqft": floor.get("value") if isinstance(floor, dict) else floor,
                "description": obj.get("description"),
                "image_url": _first_image(obj.get("image")),
                "area": area,
            }
            if rec["address"]:
                out.append(_norm(rec))
    return out


def _from_opengraph(tree: HTMLParser) -> list[dict[str, Any]]:
    meta: dict[str, str] = {}
    for node in tree.css("meta"):
        prop = node.attributes.get("property") or node.attributes.get("name")
        content = node.attributes.get("content")
        if prop and content:
            meta[prop.lower()] = content
    rec = {
        "address": meta.get("og:title"),
        "description": meta.get("og:description"),
        "image_url": meta.get("og:image"),
        "price": meta.get("product:price:amount") or meta.get("og:price:amount"),
        "area": meta.get("og:locality") or meta.get("og:region"),
    }
    if not (rec["address"] or rec["description"]):
        return []
    return [_norm(rec)]


def _text_for(tree: HTMLParser, selectors: list[str]) -> str | None:
    for sel in selectors:
        node = tree.css_first(sel)
        if node:
            txt = node.text(strip=True)
            if txt:
                return txt
    return None


def _from_dom(tree: HTMLParser) -> list[dict[str, Any]]:
    address = _text_for(
        tree,
        [
            '[itemprop="streetAddress"]',
            '[itemprop="address"]',
            ".address",
            "[data-address]",
        ],
    )
    if not address:
        return []
    rec = {
        "address": address,
        "price": _text_for(tree, ['[itemprop="price"]', ".price", "[data-price]"]),
        "beds": _text_for(
            tree, ['[itemprop="numberOfBedrooms"]', ".beds", "[data-beds]"]
        ),
        "baths": _text_for(
            tree, ['[itemprop="numberOfBathrooms"]', ".baths", "[data-baths]"]
        ),
        "sqft": _text_for(tree, ['[itemprop="floorSize"]', ".sqft", "[data-sqft]"]),
        "description": _text_for(tree, ['[itemprop="description"]', ".description"]),
    }
    return [_norm(rec)]


def _page_text(tree: HTMLParser) -> str:
    body = tree.body
    return body.text(separator=" ", strip=True) if body else ""


def _from_llm(text: str, llm: LLMExtractor) -> list[dict[str, Any]]:
    records = llm(text)
    return [_norm(r) for r in records if isinstance(r, dict) and r.get("address")]


def extract_from_html(
    html: str, *, llm: LLMExtractor | None = None
) -> list[dict[str, Any]]:
    """Run the ladder: structured data first, LLM backstop only if nothing else matched."""
    tree = HTMLParser(html)
    for extractor in (_from_jsonld, _from_opengraph, _from_dom):
        result = extractor(tree)
        if result:
            return result
    if llm is not None:
        return _from_llm(_page_text(tree), llm)
    return []


_CSV_ALIASES = {
    "address": ("address", "street", "location"),
    "price": ("price", "list_price", "amount"),
    "beds": ("beds", "bedrooms", "br"),
    "baths": ("baths", "bathrooms", "ba"),
    "sqft": ("sqft", "square_feet", "size"),
    "description": ("description", "desc", "details"),
    "code": ("code", "mls", "id", "sku"),
    "area": ("area", "neighbourhood", "neighborhood", "city"),
}


def extract_from_csv(content: str | bytes) -> list[dict[str, Any]]:
    if isinstance(content, bytes):
        content = content.decode("utf-8", errors="replace")
    out: list[dict[str, Any]] = []
    for row in csv.DictReader(io.StringIO(content)):
        lowered = {(k or "").strip().lower(): v for k, v in row.items()}
        rec: dict[str, Any] = {}
        for field, aliases in _CSV_ALIASES.items():
            for alias in aliases:
                if lowered.get(alias):
                    rec[field] = lowered[alias]
                    break
        if rec.get("address"):
            out.append(_norm(rec))
    return out


def extract_text_from_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def extract_from_pdf(
    data: bytes, *, llm: LLMExtractor | None = None
) -> list[dict[str, Any]]:
    text = extract_text_from_pdf(data)
    if llm is not None and text.strip():
        return _from_llm(text, llm)
    return []
