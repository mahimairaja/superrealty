from fastapi import APIRouter, Depends, HTTPException, status

from src.core.widget_guard import enforce_widget_guard
from src.schemas.listing_schemas import ListingDraft, ListingPatch
from src.services.onboard_service import get_staging_store

router = APIRouter(prefix="/listings", tags=["listings"])

# M0 is single-realtor with no sign-in, so `realtor` is a label rather than a tenant
# boundary (see onboard.py). The widget guard bounds anonymous abuse. POST-M0, derive
# `realtor` from the authenticated principal instead of trusting the query parameter.


@router.get("", response_model=list[ListingDraft])
async def list_listings(
    realtor: str, _: None = Depends(enforce_widget_guard)
) -> list[dict]:
    return get_staging_store().list(realtor)


@router.patch("/{draft_id}", response_model=ListingDraft)
async def patch_listing(
    draft_id: str,
    patch: ListingPatch,
    realtor: str,
    _: None = Depends(enforce_widget_guard),
) -> dict:
    updated = get_staging_store().patch(
        realtor, draft_id, patch.model_dump(exclude_unset=True)
    )
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="listing not found")
    return updated


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_listing(
    draft_id: str, realtor: str, _: None = Depends(enforce_widget_guard)
) -> None:
    if not get_staging_store().remove(realtor, draft_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="listing not found")
