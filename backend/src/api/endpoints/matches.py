from fastapi import APIRouter, Depends

from src.core.widget_guard import enforce_widget_guard
from src.schemas.match_schemas import MatchRequest, MatchResponse
from src.services import matching_service

router = APIRouter(prefix="/matches", tags=["matches"])


@router.post("", response_model=MatchResponse)
async def find_matches(
    payload: MatchRequest,
    _: None = Depends(enforce_widget_guard),
) -> MatchResponse:
    result = await matching_service.find_matches(payload.model_dump())
    return MatchResponse(**result)
