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


# Destructive. M0 is single-realtor with no sign-in, so there is no other tenant whose buyer
# could be deleted, and the agent only ever calls this with its verified caller phone
# (forget_me derives it, never an argument). Widget-guarded. POST-M0: require proof of
# possession of the phone (an OTP / signed token) before deletion.
@router.delete("/{phone}")
async def forget_buyer(
    phone: str,
    _: None = Depends(enforce_widget_guard),
) -> dict[str, object]:
    # Forget on request: remove exactly this buyer's Cognee dataset. A later call from
    # this phone is then treated as a brand-new buyer with no history.
    await get_memory_store().forget_buyer(phone)
    return {"forgotten": True, "phone": phone}
