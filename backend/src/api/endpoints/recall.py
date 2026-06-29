from typing import Any

from fastapi import APIRouter, Depends

from src.core.widget_guard import enforce_widget_guard
from src.memory.store import get_memory_store
from src.schemas.recall_schemas import RecallRequest, RecallResponse

router = APIRouter(prefix="/recall", tags=["recall"])


def _first_answer(results: list[Any]) -> str:
    """Cognee recall returns grounded completion entries; pull the first answer text."""
    if not results:
        return ""
    first = results[0]
    for attr in ("answer", "text", "content"):
        value = getattr(first, attr, None)
        if isinstance(value, str) and value:
            return value
    return str(first)


# Single-realtor M0: every connected listing belongs to the one realtor, so a graph-wide
# recall already returns only that realtor's homes (REQ-RR-CALL-002.1). POST-M0 multi-realtor:
# scope the search by the realtor's dataset / NodeSet so cross-realtor homes never leak.
@router.post("", response_model=RecallResponse)
async def recall(
    payload: RecallRequest,
    _: None = Depends(enforce_widget_guard),
) -> RecallResponse:
    results = await get_memory_store().recall(payload.criteria, top_k=payload.top_k)
    return RecallResponse(
        realtor=payload.realtor,
        answer=_first_answer(results),
        match_count=len(results),
    )
