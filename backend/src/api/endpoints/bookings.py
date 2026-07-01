from fastapi import APIRouter, status

from src.core.tenant import AgentTenant
from src.schemas.booking_schemas import BookingRequest, BookingResponse
from src.services import booking_service

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingRequest,
    tenant_id: AgentTenant,
) -> BookingResponse:
    # The agent books on behalf of the realtor it is serving. The tenant comes from the
    # authenticated agent request (X-Tenant-Id behind the shared secret), not the payload,
    # so a booking is always stamped to the right realtor's calendar and memory.
    result = await booking_service.book_showing(payload.model_dump(), tenant_id)
    return BookingResponse(**result)
