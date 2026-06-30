import logging

from fastapi import APIRouter, Depends

from src.core.config import config
from src.core.widget_guard import enforce_widget_guard
from src.memory.store import buyer_dataset, get_memory_store
from src.repository import call_log_repository
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
    row = await call_log_repository.create({"room_name": room, **payload.model_dump()})
    if payload.buyer_phone:
        try:
            await get_memory_store().improve(dataset=buyer_dataset(payload.buyer_phone))
        except Exception as exc:  # noqa: BLE001
            logger.warning("improve on call close failed: %s", exc)
    await _maybe_send_lead_sms(payload)
    return CallCloseResponse(id=row.id, room_name=room)


async def _maybe_send_lead_sms(payload: CallClose) -> None:
    """Text the realtor the buyer details so they can follow up fast. Best-effort; only
    fires when Telnyx and the realtor's number are configured.
    """
    api_key = (
        config.TELNYX_API_KEY.get_secret_value() if config.TELNYX_API_KEY else None
    )
    if not (api_key and config.TELNYX_FROM_NUMBER and config.REALTOR_SMS_TO):
        return
    text = payload.summary or (
        f"New RealtyRecall call ({payload.outcome or 'completed'})."
        + (f" Buyer: {payload.buyer_phone}." if payload.buyer_phone else "")
    )
    try:
        await sms_service.send_sms(
            to=config.REALTOR_SMS_TO,
            text=text,
            api_key=api_key,
            from_number=config.TELNYX_FROM_NUMBER,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("lead handoff SMS failed: %s", exc)
