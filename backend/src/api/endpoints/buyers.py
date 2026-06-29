from fastapi import APIRouter, Depends, status

from src.core.widget_guard import enforce_widget_guard
from src.memory.store import get_memory_store
from src.schemas.buyer_schemas import BuyerRecall, BuyerUpsert, BuyerUpsertResponse

router = APIRouter(prefix="/buyers", tags=["buyers"])


@router.post(
    "", response_model=BuyerUpsertResponse, status_code=status.HTTP_201_CREATED
)
async def upsert_buyer(
    payload: BuyerUpsert,
    _: None = Depends(enforce_widget_guard),
) -> BuyerUpsertResponse:
    # Buyers are keyed by phone and owned by Cognee (a per-buyer dataset). Upsert is
    # safe to call repeatedly: a return call updates what we remember.
    await get_memory_store().upsert_buyer(payload.model_dump())
    return BuyerUpsertResponse(phone=payload.phone, name=payload.name)


@router.get("/{phone}", response_model=BuyerRecall)
async def get_buyer(
    phone: str,
    _: None = Depends(enforce_widget_guard),
) -> BuyerRecall:
    # On call start the assistant looks up the caller by phone. Always 200; found=false
    # means a new (or forgotten) buyer, so the agent opens as if it is a first call.
    result = await get_memory_store().get_buyer(phone)
    return BuyerRecall(**result)
