from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from src.core.clerk import CurrentTenant
from src.core.tenant import AgentTenant
from src.memory.graph_service import get_graph_service
from src.memory.store import get_memory_store
from src.schemas.listing_schemas import (
    ListingCreate,
    ListingDraft,
    ListingPatch,
    LiveListing,
)
from src.services.onboard_service import StagedStore

router = APIRouter(prefix="/listings", tags=["listings"])

# The staging buffer is keyed by the Clerk-verified tenant (the realtor's org), so one
# realtor can only ever review, edit, or remove their own staged listings. Any `realtor`
# query param the console still sends is ignored (FastAPI drops unexpected params).


@router.get("", response_model=list[ListingDraft])
async def list_listings(tenant_id: CurrentTenant, store: StagedStore) -> list[dict]:
    return await store.list(tenant_id)


@router.post("", response_model=LiveListing, status_code=status.HTTP_201_CREATED)
async def create_listing(payload: ListingCreate, tenant_id: CurrentTenant) -> dict:
    # Add one home straight to the live catalog (a manual console add). It becomes the newest
    # listing, so the "Buyers waiting" match card immediately reflects it. A code is generated
    # when omitted so the match lookup (keyed by code) always has one.
    item = payload.model_dump()
    if not item.get("code"):
        item["code"] = f"NEW-{uuid4().hex[:6].upper()}"
    return await get_memory_store().add_single_listing(tenant_id, item)


@router.get("/live", response_model=list[LiveListing])
async def list_live_listings(tenant_id: CurrentTenant) -> list[dict]:
    # The realtor's connected homes, read back from Cognee (what the assistant actually
    # recommends). This is the post-confirm view: staging clears on confirm, these persist.
    return await get_memory_store().list_listings(tenant_id)


@router.get("/catalog", response_model=list[LiveListing])
async def listing_catalog(tenant_id: AgentTenant) -> list[dict]:
    # Same connected homes as /live, but for the AGENT (agent-secret gated, not Clerk): the
    # assistant fetches the structured catalog to push house cards to the caller's screen
    # during a call. Identical data, different caller/auth than the console.
    return await get_memory_store().list_listings(tenant_id)


@router.get("/{code}/matches")
async def listing_matches(code: str, tenant_id: CurrentTenant) -> dict:
    # Which remembered buyers want this specific connected listing (graph match). Powers the
    # "N buyers want this" card and the proactive-notify story.
    listings = await get_memory_store().list_listings(tenant_id)
    listing = next((h for h in listings if str(h.get("code")) == code), None)
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="listing not found")
    return await get_graph_service().match_report(tenant_id, listing)


@router.patch("/{draft_id}", response_model=ListingDraft)
async def patch_listing(
    draft_id: str,
    patch: ListingPatch,
    tenant_id: CurrentTenant,
    store: StagedStore,
) -> dict:
    updated = await store.patch(
        tenant_id, draft_id, patch.model_dump(exclude_unset=True)
    )
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="listing not found")
    return updated


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_listing(
    draft_id: str, tenant_id: CurrentTenant, store: StagedStore
) -> None:
    if not await store.remove(tenant_id, draft_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="listing not found")
