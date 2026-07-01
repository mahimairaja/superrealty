import asyncio

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from src.core.clerk import CurrentTenant
from src.memory.store import get_memory_store
from src.schemas.listing_schemas import (
    ConfirmResponse,
    ListingDraft,
    OnboardResponse,
    RealtorProfile,
)
from src.services import fetch_service, ingest_service
from src.services.onboard_service import StagedStore, extract_drafts

router = APIRouter(prefix="/onboard", tags=["onboard"])


# The realtor console authenticates with Clerk; the staging buffer and the Cognee write are
# keyed by the verified tenant (their org), so two realtors never see or confirm each other's
# staged listings. `realtor` is now just the display name written onto the Realtor node.
@router.post("", response_model=OnboardResponse, status_code=status.HTTP_201_CREATED)
async def onboard(
    tenant_id: CurrentTenant,
    store: StagedStore,
    realtor: str = Form(""),  # optional: the URL flow infers the name from the site
    authorized: bool = Form(False),
    file: UploadFile | None = File(None),
    url: str | None = Form(None),
) -> OnboardResponse:
    # Consent gate: the realtor must affirm they are authorized to use these listings before
    # we fetch or read anything. Nothing goes live here; it is staged for their review.
    if not authorized:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="confirm you are authorized to use these listings",
        )

    profile: dict | None = None
    if url:
        # Fan-out: crawl the realtor's OWN site from the seed URL and extract every listing
        # plus a short profile. Bounded by a deadline so a slow site can't hang the request.
        try:
            drafts, profile = await asyncio.wait_for(
                ingest_service.ingest_url(url), timeout=75.0
            )
        except fetch_service.FetchError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"couldn't read that URL: {exc}",
            ) from exc
        except TimeoutError as exc:
            raise HTTPException(
                status.HTTP_504_GATEWAY_TIMEOUT,
                detail="that site took too long; try the file upload instead",
            ) from exc
    elif file is not None:
        drafts = extract_drafts(await file.read(), file.filename)
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail="provide a listings URL or file"
        )

    # Drop anything without a clean string address so a malformed record can't 500 the
    # response build (ListingDraft requires a str address) or reach the assistant.
    drafts = [
        d for d in drafts if isinstance(d.get("address"), str) and d["address"].strip()
    ]

    # A URL crawl that fetched fine but found no listings still succeeds (200) and keeps the
    # inferred profile, so the console can show a friendly "no listings" state; only the file
    # path treats an empty result as unreadable input.
    if not drafts and not url:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="no listings could be read; try a CSV or PDF, or a different URL",
        )

    # Replace, not append: clearing first means the set the realtor reviews is exactly the set
    # that goes live, even if they re-fetch or switch between URL and file before confirming.
    await store.clear(tenant_id)
    staged = await store.stage(tenant_id, drafts)
    await store.stage_profile(tenant_id, profile)
    return OnboardResponse(
        realtor=(profile or {}).get("name") or realtor,
        listings=[ListingDraft(**d) for d in staged],
        profile=RealtorProfile(**profile) if profile else None,
    )


@router.post("/confirm", response_model=ConfirmResponse)
async def confirm(
    tenant_id: CurrentTenant,
    store: StagedStore,
    realtor: str = Form(""),
) -> ConfirmResponse:
    # Insert the reviewed staging set into the tenant's Cognee memory (the system of record).
    drafts = await store.list(tenant_id)
    if not drafts:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="nothing staged for this realtor"
        )
    profile = await store.get_profile(tenant_id) or {}
    name = profile.get("name") or realtor
    # Persist the whole inferred persona onto the Realtor node, not just the name, so the live
    # voice agent can answer in the realtor's name, agency, and tone.
    realtor_meta = {
        "name": name,
        "agency": profile.get("agency"),
        "area": profile.get("area"),
        "tagline": profile.get("tagline"),
        "tone": profile.get("tone"),
    }
    await get_memory_store().add_listings(tenant_id, realtor_meta, drafts)
    await store.clear(tenant_id)
    return ConfirmResponse(realtor=name, inserted=len(drafts))
