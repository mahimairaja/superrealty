from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from src.core.container import Container
from src.core.widget_guard import enforce_widget_guard
from src.repository import tenant_repository
from src.schemas.token_schemas import RoomTokenRequest, RoomTokenResponse
from src.services.token_service import TokenService

router = APIRouter(prefix="/token", tags=["token"])


@router.post("", response_model=RoomTokenResponse, status_code=status.HTTP_201_CREATED)
@inject
async def create_room_token(
    payload: RoomTokenRequest,
    _: None = Depends(enforce_widget_guard),
    service: TokenService = Depends(Provide[Container.token_service]),
) -> RoomTokenResponse:
    # Public by default. To require an authenticated user, add the dependency
    # `current_user: CurrentUser` (see src/api/endpoints/users.py) to this
    # signature; LiveKit room tokens are unrelated to the backend's own JWT.
    #
    # The tenant slug is public (it lives in the realtor's call link), but it must
    # name a real tenant: otherwise a caller could spin up rooms under arbitrary
    # slugs. A LiveKit token only grants entry to its own room, so this is a
    # validity gate, not an auth boundary. Unknown slug -> 404.
    if (
        payload.tenant
        and await tenant_repository.get_by_clerk_org_id(payload.tenant) is None
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown tenant")
    return service.create_room_token(payload)
