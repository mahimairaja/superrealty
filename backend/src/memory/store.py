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
from uuid import NAMESPACE_OID, uuid5

import asyncpg
import cognee
from cognee import SearchType
from cognee.modules.engine.models import NodeSet
from cognee.modules.engine.operations.setup import setup as cognee_setup
from cognee.tasks.storage import add_data_points

from src.memory.models import Buyer, Listing, Neighbourhood, Realtor, Showing

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


def tenant_tag(tenant_id: str) -> str:
    """The NodeSet name that scopes every graph node to one realtor (tenant). Recall and
    buyer-matching search only within this set, so one realtor never sees another's data.
    """
    return f"tenant_{tenant_id}"


def _tenant_nodeset(tenant_id: str) -> NodeSet:
    """A stable NodeSet for the tenant: typed nodes are tagged with it on write, and search
    filters by it on read. The id is derived from the name so every write reuses one set.
    """
    name = tenant_tag(tenant_id)
    return NodeSet(id=uuid5(NAMESPACE_OID, name=name), name=name)


def listings_dataset(tenant_id: str) -> str:
    """The tenant's listings dataset (the buyer text flow and improve are dataset-scoped)."""
    return f"tenant_{tenant_id}_listings"


def buyer_dataset(tenant_id: str, phone: str) -> str:
    """Each buyer gets its own per-tenant dataset so forget removes exactly that buyer and a
    shared phone number never collides across realtors.
    """
    digits = re.sub(r"\D", "", phone or "")
    return f"tenant_{tenant_id}_buyer_{digits}"


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
    """The realty memory: listings and buyers, backed by Cognee.

    Every operation is scoped to a tenant (the realtor's Clerk org). Typed graph nodes are
    tagged with the tenant's NodeSet on write and search filters by it on read, and the
    per-buyer text datasets are namespaced by tenant, so one realtor's listings and buyers
    are never visible to another's.
    """

    async def add_listings(
        self, tenant_id: str, realtor: dict[str, Any], listings: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Add a realtor and their listings as typed graph nodes, tagged with the tenant's
        NodeSet so recall and matching stay scoped to this realtor.
        """
        await ensure_cognee()
        nodeset = _tenant_nodeset(tenant_id)
        realtor_node = Realtor(name=realtor["name"], email=realtor.get("email"))
        points: list[Any] = [realtor_node]
        represented: list[Any] = []
        for item in listings:
            hood = None
            area = item.get("area") or item.get("neighbourhood")
            if area:
                hood = Neighbourhood(name=area, city=item.get("city"))
                hood.belongs_to_set = [nodeset]
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
            listing.belongs_to_set = [nodeset]
            points.append(listing)
            represented.append(listing)
        realtor_node.represents = represented
        realtor_node.belongs_to_set = [nodeset]
        await add_data_points(points)
        return listings

    async def recall(
        self, tenant_id: str, criteria: dict[str, Any] | str, top_k: int = 5
    ) -> list[Any]:
        """Recall listings matching a buyer's criteria (or a raw query), scoped to the
        tenant's NodeSet so one realtor never sees another's listings.
        """
        await ensure_cognee()
        query = criteria if isinstance(criteria, str) else _criteria_to_text(criteria)
        results: list[Any] = await cognee.search(
            query_text=query,
            query_type=SearchType.GRAPH_COMPLETION,
            node_type=NodeSet,
            node_name=[tenant_tag(tenant_id)],
            top_k=top_k,
        )
        return results

    async def match_buyers(self, tenant_id: str, listing: dict[str, Any]) -> str:
        """Find buyers whose stated criteria match a (newly added) listing, with which of
        their wishes it meets. Scoped to this tenant's NodeSet (typed Buyer + Listing nodes).
        """
        await ensure_cognee()
        parts: list[str] = []
        if listing.get("area"):
            parts.append(f"in {listing['area']}")
        if listing.get("beds"):
            parts.append(f"{listing['beds']} bedrooms")
        if listing.get("price"):
            parts.append(f"around {listing['price']}")
        desc = ", ".join(parts) if parts else "this home"
        query = (
            f"A new home is available ({desc}). Which remembered buyers are looking for a "
            "home like this? Name each matching buyer and which of their wishes it meets."
        )
        results: list[Any] = await cognee.search(
            query_text=query,
            query_type=SearchType.GRAPH_COMPLETION,
            node_type=NodeSet,
            node_name=[tenant_tag(tenant_id)],
            top_k=5,
        )
        return str(results[0]) if results else ""

    async def upsert_buyer(
        self, tenant_id: str, buyer: dict[str, Any]
    ) -> dict[str, Any]:
        """Remember (or update) a buyer: a typed Buyer node plus a per-buyer, per-tenant
        dataset so forget removes exactly them and a return call can recall them.
        """
        await ensure_cognee()
        nodeset = _tenant_nodeset(tenant_id)
        node = Buyer(
            phone=buyer["phone"],
            name=buyer.get("name"),
            email=buyer.get("email"),
            criteria=buyer.get("criteria"),
        )
        node.belongs_to_set = [nodeset]
        await add_data_points([node])
        # Keep a per-buyer, per-tenant dataset (cognified so it is searchable) so forget_buyer
        # removes exactly this buyer and get_buyer can recall them on a return call. node_set
        # tags the cognified text too, so a shared phone never crosses tenants. Skip this when
        # the phone has no digits, so phoneless buyers never collapse into one shared
        # tenant_{tid}_buyer_ dataset (forget would otherwise wipe them all).
        if re.sub(r"\D", "", buyer["phone"] or ""):
            dataset = buyer_dataset(tenant_id, buyer["phone"])
            await cognee.add(
                _buyer_to_text(buyer),
                dataset_name=dataset,
                node_set=[tenant_tag(tenant_id)],
            )
            await cognee.cognify(datasets=[dataset])
        return buyer

    async def get_buyer(self, tenant_id: str, phone: str) -> dict[str, Any]:
        """Recall a returning buyer by phone: name, prior criteria, homes discussed.

        Searches only the buyer's own per-tenant dataset. Always returns a dict; found=False
        means a new (or forgotten) buyer.
        """
        await ensure_cognee()
        dataset = buyer_dataset(tenant_id, phone)
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

    async def add_showing(
        self,
        *,
        tenant_id: str,
        phone: str | None,
        property_code: str | None,
        address: str | None,
        when_utc: str,
    ) -> None:
        """Record a booked showing: a Showing node plus a note folded into the buyer's
        dataset so a later recall mentions it. Both are scoped to the tenant.
        """
        await ensure_cognee()
        showing = Showing(when_utc=when_utc)
        showing.belongs_to_set = [_tenant_nodeset(tenant_id)]
        await add_data_points([showing])
        dataset = (
            buyer_dataset(tenant_id, phone) if phone else listings_dataset(tenant_id)
        )
        note = f"A showing is booked for {address or property_code} on {when_utc}"
        note += f" for the buyer at {phone}." if phone else "."
        await cognee.add(note, dataset_name=dataset, node_set=[tenant_tag(tenant_id)])

    async def improve(self, tenant_id: str, phone: str | None = None) -> None:
        """Fold the latest understanding back into memory. Scoped to the buyer's dataset when
        a phone is given, else the tenant's listings dataset.
        """
        await ensure_cognee()
        dataset = (
            buyer_dataset(tenant_id, phone) if phone else listings_dataset(tenant_id)
        )
        await cognee.improve(dataset=dataset)

    async def forget_buyer(self, tenant_id: str, phone: str) -> dict[str, Any]:
        """Forget a buyer by removing their per-tenant Cognee dataset exactly."""
        await ensure_cognee()
        result: dict[str, Any] = await cognee.forget(
            dataset=buyer_dataset(tenant_id, phone)
        )
        return result


_store: MemoryStore | None = None


def get_memory_store() -> MemoryStore:
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store
