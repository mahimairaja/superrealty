import logging

from fastapi import APIRouter, Depends

from src.core.config import config
from src.core.tenant import tenant_from_room_name
from src.core.widget_guard import enforce_widget_guard
from src.memory.store import get_memory_store
from src.repository import call_log_repository, tenant_repository
from src.schemas.call_schemas import CallClose, CallCloseResponse
from src.services import sms_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calls", tags=["calls"])


# M0 is single-realtor with no sign-in, so there is no other tenant whose room/buyer this
# could cross, and the agent posts buyer_phone = its verified caller phone. Widget-guarded.
# POST-M0: validate a server-issued room token (the agent for `room`) and resolve buyer_phone
# from the call's authoritative record rather than the body, so improve() cannot be aimed at
# another buyer's memory.
@router.post("/{room}/close", response_model=CallCloseResponse)
async def close_call(
    room: str,
    payload: CallClose,
    _: None = Depends(enforce_widget_guard),
) -> CallCloseResponse:
    # Persist the call log, then fold the conversation into permanent memory so the latest
    # buyer understanding wins (improve is best-effort and never breaks the close).
    # The tenant is recovered from the room name (t_{tenant}_{random}), which the backend
    # minted and LiveKit signed, so it stamps the row to the right realtor.
    tenant_id = tenant_from_room_name(room)
    row = await call_log_repository.create(
        {"room_name": room, "tenant_id": tenant_id, **payload.model_dump()}
    )
    if tenant_id and payload.buyer_phone:
        try:
            await get_memory_store().improve(
                tenant_id=tenant_id, phone=payload.buyer_phone
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("improve on call close failed: %s", exc)
    await _maybe_send_lead_sms(payload, tenant_id)
    return CallCloseResponse(id=row.id, room_name=room)


async def _maybe_send_lead_sms(payload: CallClose, tenant_id: str | None) -> None:
    """Text the realtor the buyer details so they can follow up fast. Best-effort; only fires
    when Telnyx is configured and the realtor has a number (their per-tenant Settings number,
    falling back to the global REALTOR_SMS_TO for the single-realtor demo).
    """
    api_key = (
        config.TELNYX_API_KEY.get_secret_value() if config.TELNYX_API_KEY else None
    )
    if not (api_key and config.TELNYX_FROM_NUMBER):
        return
    to = None
    if tenant_id:
        tenant = await tenant_repository.get_by_clerk_org_id(tenant_id)
        to = tenant.sms_to if tenant else None
    to = to or config.REALTOR_SMS_TO
    if not to:
        return
    text = payload.summary or (
        f"New RealtyRecall call ({payload.outcome or 'completed'})."
        + (f" Buyer: {payload.buyer_phone}." if payload.buyer_phone else "")
    )
    try:
        await sms_service.send_sms(
            to=to,
            text=text,
            api_key=api_key,
            from_number=config.TELNYX_FROM_NUMBER,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("lead handoff SMS failed: %s", exc)
