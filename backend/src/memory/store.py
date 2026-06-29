"""Async wrapper over Cognee: the system of record for listings and buyers.

Cognee owns the graph (Neo4j) and vectors (pgvector). This module configures Cognee
programmatically from the backend settings (so Cognee's relational DB_* names do not
collide with the backend's operational DB_*), and exposes the memory operations the API
and the agent rely on: add listings, recall by criteria, upsert a buyer, improve after a
call, and forget a buyer (its own dataset, removed exactly).
"""

from __future__ import annotations

import os
import re
from typing import Any

import asyncpg
import cognee
from cognee import SearchType
from cognee.modules.engine.operations.setup import setup as cognee_setup
from cognee.tasks.storage import add_data_points

from src.memory.models import Buyer, Listing, Neighbourhood, Realtor

LISTINGS_DATASET = "listings"
_configured = False
_setup_done = False


def _pg_url() -> str:
    user = os.getenv("DB_USERNAME") or os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("COGNEE_DB_NAME", "cognee_db")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


async def _ensure_cognee_db() -> None:
    """Create the dedicated Cognee database and the pgvector extension if missing.

    Cognee is isolated in its own database so its tables (it creates a 'users' table for
    access control, among others) never collide with the operational schema.
    """
    name = os.getenv("COGNEE_DB_NAME", "cognee_db")
    user = os.getenv("DB_USERNAME") or os.getenv("DB_USER") or "postgres"
    password = os.getenv("DB_PASSWORD", "postgres")
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5432"))
    admin = await asyncpg.connect(
        user=user, password=password, host=host, port=port, database="postgres"
    )
    try:
        exists = await admin.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", name
        )
        if not exists:
            await admin.execute(f'CREATE DATABASE "{name}"')
    finally:
        await admin.close()
    db = await asyncpg.connect(
        user=user, password=password, host=host, port=port, database=name
    )
    try:
        await db.execute("CREATE EXTENSION IF NOT EXISTS vector")
    finally:
        await db.close()


def configure_cognee() -> None:
    """Point Cognee at Neo4j + pgvector + OpenAI. Idempotent."""
    global _configured
    if _configured:
        return

    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if api_key:
        cognee.config.set_llm_api_key(api_key)
    # Single-realtor demo: no multi-user access control (Cognee 1.x default is on).
    os.environ.setdefault("ENABLE_BACKEND_ACCESS_CONTROL", "false")

    cognee.config.set_graph_database_provider(
        os.getenv("GRAPH_DATABASE_PROVIDER", "neo4j")
    )
    try:
        cognee.config.set_graph_db_config(
            {
                "graph_database_provider": os.getenv(
                    "GRAPH_DATABASE_PROVIDER", "neo4j"
                ),
                "graph_database_url": os.getenv(
                    "GRAPH_DATABASE_URL", "bolt://localhost:7687"
                ),
                "graph_database_name": os.getenv("GRAPH_DATABASE_NAME", "neo4j"),
                "graph_database_username": os.getenv(
                    "GRAPH_DATABASE_USERNAME", "neo4j"
                ),
                "graph_database_password": os.getenv(
                    "GRAPH_DATABASE_PASSWORD", "neo4jpassword"
                ),
            }
        )
    except Exception:
        # Env vars cover the same config if the dict keys differ across Cognee versions.
        pass

    cognee.config.set_vector_db_provider("pgvector")
    cognee.config.set_vector_db_url(_pg_url())
    try:
        cognee.config.set_relational_db_config(
            {
                "db_provider": "postgres",
                "db_name": os.getenv("COGNEE_DB_NAME", "cognee_db"),
                "db_host": os.getenv("DB_HOST", "localhost"),
                "db_port": os.getenv("DB_PORT", "5432"),
                "db_username": os.getenv("DB_USERNAME")
                or os.getenv("DB_USER")
                or "postgres",
                "db_password": os.getenv("DB_PASSWORD", "postgres"),
            }
        )
    except Exception:
        pass

    _configured = True


async def ensure_cognee() -> None:
    """Configure Cognee and run its one-time setup (system tables + default user)."""
    global _setup_done
    configure_cognee()
    if not _setup_done:
        await _ensure_cognee_db()
        await cognee_setup()
        _setup_done = True


def buyer_dataset(phone: str) -> str:
    """Each buyer gets its own dataset so forget removes exactly that buyer."""
    digits = re.sub(r"\D", "", phone or "")
    return f"buyer-{digits}"


def _criteria_to_text(criteria: dict[str, Any]) -> str:
    parts: list[str] = []
    if criteria.get("area"):
        parts.append(f"in {criteria['area']}")
    if criteria.get("maxPrice"):
        parts.append(f"under {criteria['maxPrice']}")
    if criteria.get("minBeds"):
        parts.append(f"at least {criteria['minBeds']} bedrooms")
    want = ", ".join(parts) if parts else "any home"
    return f"Which connected listings match a buyer looking for {want}?"


def _buyer_to_text(buyer: dict[str, Any]) -> str:
    name = buyer.get("name") or "A buyer"
    return f"{name} (phone {buyer.get('phone')}) is a buyer. Criteria: {buyer.get('criteria') or {}}."


class MemoryStore:
    """The realty memory: listings and buyers, backed by Cognee."""

    async def add_listings(
        self, realtor: dict[str, Any], listings: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        await ensure_cognee()
        realtor_node = Realtor(name=realtor["name"], email=realtor.get("email"))
        points: list[Any] = [realtor_node]
        represented: list[Any] = []
        for item in listings:
            hood = None
            area = item.get("area") or item.get("neighbourhood")
            if area:
                hood = Neighbourhood(name=area, city=item.get("city"))
                points.append(hood)
            listing = Listing(
                code=item["code"],
                address=item["address"],
                price=item.get("price"),
                beds=item.get("beds"),
                baths=item.get("baths"),
                sqft=item.get("sqft"),
                description=item.get("description"),
                image_url=item.get("image_url"),
                located_in=hood,
            )
            points.append(listing)
            represented.append(listing)
        realtor_node.represents = represented
        await add_data_points(points)
        return listings

    async def recall(self, criteria: dict[str, Any] | str, top_k: int = 5) -> list[Any]:
        await ensure_cognee()
        query = criteria if isinstance(criteria, str) else _criteria_to_text(criteria)
        results: list[Any] = await cognee.search(
            query_text=query,
            query_type=SearchType.GRAPH_COMPLETION,
            top_k=top_k,
        )
        return results

    async def upsert_buyer(self, buyer: dict[str, Any]) -> dict[str, Any]:
        await ensure_cognee()
        node = Buyer(
            phone=buyer["phone"],
            name=buyer.get("name"),
            email=buyer.get("email"),
            criteria=buyer.get("criteria"),
        )
        await add_data_points([node])
        # Keep a per-buyer dataset (cognified so it is searchable) so forget_buyer removes
        # exactly this buyer and get_buyer can recall them on a return call.
        dataset = buyer_dataset(buyer["phone"])
        await cognee.add(_buyer_to_text(buyer), dataset_name=dataset)
        await cognee.cognify(datasets=[dataset])
        return buyer

    async def get_buyer(self, phone: str) -> dict[str, Any]:
        """Recall a returning buyer by phone: name, prior criteria, homes discussed.

        Searches only the buyer's own dataset. Always returns a dict; found=False means a
        new (or forgotten) buyer.
        """
        await ensure_cognee()
        dataset = buyer_dataset(phone)
        try:
            results = await cognee.search(
                query_text=(
                    "Summarize this returning buyer: their name, their stated criteria "
                    "(area, budget, bedrooms), and any homes they discussed."
                ),
                query_type=SearchType.GRAPH_COMPLETION,
                datasets=[dataset],
                top_k=5,
            )
        except Exception:  # noqa: BLE001  (unknown/forgotten buyer -> not found)
            results = []
        if not results:
            return {"found": False, "phone": phone}
        return {"found": True, "phone": phone, "summary": str(results[0])}

    async def improve(self, dataset: str = LISTINGS_DATASET) -> None:
        await ensure_cognee()
        await cognee.improve(dataset=dataset)

    async def forget_buyer(self, phone: str) -> dict[str, Any]:
        await ensure_cognee()
        result: dict[str, Any] = await cognee.forget(dataset=buyer_dataset(phone))
        return result


_store: MemoryStore | None = None


def get_memory_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store
