from fastapi import APIRouter, status

from src.core.tenant import AgentTenant
from src.memory.store import get_memory_store
from src.schemas.buyer_schemas import (
    BuyerForgetResponse,
    BuyerRecall,
    BuyerUpsert,
    BuyerUpsertResponse,
)

router = APIRouter(prefix="/buyers", tags=["buyers"])


@router.post(
    "", response_model=BuyerUpsertResponse, status_code=status.HTTP_201_CREATED
)
async def upsert_buyer(
    payload: BuyerUpsert,
    tenant_id: AgentTenant,
) -> BuyerUpsertResponse:
    # Buyers are keyed by phone within the realtor's tenant and owned by Cognee (a per-buyer,
    # per-tenant dataset). Upsert is safe to call repeatedly: a return call updates memory.
    await get_memory_store().upsert_buyer(tenant_id, payload.model_dump())
    return BuyerUpsertResponse(phone=payload.phone, name=payload.name)


@router.get("/{phone}", response_model=BuyerRecall)
async def get_buyer(
    phone: str,
    tenant_id: AgentTenant,
) -> BuyerRecall:
    # On call start the assistant looks up the caller by phone within this realtor's tenant.
    # Always 200; found=false means a new (or forgotten) buyer, so the agent opens fresh.
    result = await get_memory_store().get_buyer(tenant_id, phone)
    return BuyerRecall(**result)


# Destructive, so it requires the agent secret (AgentTenant) and only ever removes a buyer
# within the asserting realtor's tenant. The agent calls this with its verified caller phone
# (forget_me derives it, never an argument). POST-M0: also require proof of possession of the
# phone (an OTP / signed token) before deletion.
@router.delete("/{phone}", response_model=BuyerForgetResponse)
async def forget_buyer(
    phone: str,
    tenant_id: AgentTenant,
) -> BuyerForgetResponse:
    # Forget on request: remove exactly this buyer's per-tenant Cognee dataset. A later call
    # from this phone is then treated as a brand-new buyer with no history.
    await get_memory_store().forget_buyer(tenant_id, phone)
    return BuyerForgetResponse(forgotten=True, phone=phone)
