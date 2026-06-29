from fastapi import APIRouter, Depends

from src.core.config import config
from src.core.widget_guard import enforce_widget_guard
from src.schemas.availability_schemas import AvailabilityDay, AvailabilityResponse
from src.services import cal_service

router = APIRouter(prefix="/availability", tags=["availability"])


@router.get("", response_model=AvailabilityResponse)
async def availability(_: None = Depends(enforce_widget_guard)) -> AvailabilityResponse:
    # Degrade to an empty slate when cal.com is not configured, so the agent offers to
    # take details and follow up rather than erroring.
    tz = config.CAL_DEFAULT_TIMEZONE
    api_key = config.CAL_API_KEY.get_secret_value() if config.CAL_API_KEY else None
    if not api_key or config.RR_CAL_EVENT_TYPE_ID is None:
        return AvailabilityResponse(timezone=tz, days=[])
    days = await cal_service.get_available_slots(
        event_type_id=config.RR_CAL_EVENT_TYPE_ID, api_key=api_key, timezone=tz
    )
    return AvailabilityResponse(
        timezone=tz, days=[AvailabilityDay(**d) for d in days]
    )
