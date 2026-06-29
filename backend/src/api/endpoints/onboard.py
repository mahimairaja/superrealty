from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from src.core.widget_guard import enforce_widget_guard
from src.memory.store import get_memory_store
from src.schemas.listing_schemas import ConfirmResponse, ListingDraft, OnboardResponse
from src.services.onboard_service import extract_drafts, get_staging_store

router = APIRouter(prefix="/onboard", tags=["onboard"])


# M0 is single-realtor with no sign-in (accounts + multi-tenancy are out of scope per the
# spec), so `realtor` is a label, not a tenant boundary, and there is no authenticated
# principal to derive it from. The widget guard (origin allowlist + per-IP rate limit)
# bounds anonymous abuse of these public write endpoints. POST-M0, once auth exists: derive
# `realtor` from the authenticated principal and drop it from the request body.
@router.post("", response_model=OnboardResponse, status_code=status.HTTP_201_CREATED)
async def onboard(
    realtor: str = Form(...),
    authorized: bool = Form(False),
    file: UploadFile | None = File(None),
    _: None = Depends(enforce_widget_guard),
) -> OnboardResponse:
    # The realtor must confirm these are their own listings before anything is staged.
    if not authorized:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="confirm you are authorized to use these listings",
        )
    if file is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="provide a listings file"
        )
    drafts = extract_drafts(await file.read(), file.filename)
    if not drafts:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="no listings could be read; try uploading a CSV or PDF instead",
        )
    staged = get_staging_store().stage(realtor, drafts)
    return OnboardResponse(
        realtor=realtor, listings=[ListingDraft(**d) for d in staged]
    )


@router.post("/confirm", response_model=ConfirmResponse)
async def confirm(
    realtor: str = Form(...),
    _: None = Depends(enforce_widget_guard),
) -> ConfirmResponse:
    # Insert the reviewed staging set into the Cognee memory graph (system of record).
    drafts = get_staging_store().list(realtor)
    if not drafts:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="nothing staged for this realtor"
        )
    await get_memory_store().add_listings({"name": realtor}, drafts)
    get_staging_store().clear(realtor)
    return ConfirmResponse(realtor=realtor, inserted=len(drafts))
