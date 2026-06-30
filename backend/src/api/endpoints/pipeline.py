from fastapi import APIRouter

from src.core.clerk import CurrentTenant
from src.repository import booking_repository, call_log_repository
from src.schemas.pipeline_schemas import (
    PipelineBooking,
    PipelineCall,
    PipelineResponse,
)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.get("", response_model=PipelineResponse)
async def pipeline(tenant_id: CurrentTenant) -> PipelineResponse:
    # The realtor view: recent bookings and calls (the connected homes and tracked buyers
    # live in Cognee and are shown via the memory-graph visualization). Scoped to the
    # signed-in realtor's tenant (Clerk org), so one realtor never sees another's pipeline.
    bookings = await booking_repository.list_recent(tenant_id=tenant_id)
    calls = await call_log_repository.list_recent(tenant_id=tenant_id)
    return PipelineResponse(
        bookings=[
            PipelineBooking(
                id=b.id,
                address=b.address,
                status=b.status,
                start_utc=b.start_utc,
                phone=b.phone,
            )
            for b in bookings
        ],
        calls=[
            PipelineCall(
                id=c.id,
                room_name=c.room_name,
                outcome=c.outcome,
                buyer_phone=c.buyer_phone,
                ended_at=c.ended_at,
            )
            for c in calls
        ],
    )
