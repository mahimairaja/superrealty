from fastapi import APIRouter, HTTPException, status

from src.core.clerk import CurrentTenant
from src.memory.store import get_memory_store
from src.schemas.listing_schemas import ListingDraft, ListingPatch, LiveListing
from src.services.onboard_service import get_staging_store

router = APIRouter(prefix="/listings", tags=["listings"])

# The staging buffer is keyed by the Clerk-verified tenant (the realtor's org), so one
# realtor can only ever review, edit, or remove their own staged listings. Any `realtor`
# query param the console still sends is ignored (FastAPI drops unexpected params).


@router.get("", response_model=list[ListingDraft])
async def list_listings(tenant_id: CurrentTenant) -> list[dict]:
    return get_staging_store().list(tenant_id)


@router.get("/live", response_model=list[LiveListing])
async def list_live_listings(tenant_id: CurrentTenant) -> list[dict]:
    # The realtor's connected homes, read back from Cognee (what the assistant actually
    # recommends). This is the post-confirm view: staging clears on confirm, these persist.
    return await get_memory_store().list_listings(tenant_id)


@router.patch("/{draft_id}", response_model=ListingDraft)
async def patch_listing(
    draft_id: str,
    patch: ListingPatch,
    tenant_id: CurrentTenant,
) -> dict:
    updated = get_staging_store().patch(
        tenant_id, draft_id, patch.model_dump(exclude_unset=True)
    )
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="listing not found")
    return updated


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_listing(draft_id: str, tenant_id: CurrentTenant) -> None:
    if not get_staging_store().remove(tenant_id, draft_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="listing not found")
