from fastapi import APIRouter

from src.core.clerk import CurrentTenant
from src.repository import tenant_repository
from src.schemas.settings_schemas import SettingsResponse, SettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(tenant_id: CurrentTenant) -> SettingsResponse:
    # Console (Clerk-gated): the realtor's own account settings. Currently just the number
    # their post-call lead texts go to.
    tenant = await tenant_repository.get_by_clerk_org_id(tenant_id)
    return SettingsResponse(sms_to=tenant.sms_to if tenant else None)


@router.patch("", response_model=SettingsResponse)
async def update_settings(
    tenant_id: CurrentTenant, body: SettingsUpdate
) -> SettingsResponse:
    tenant = await tenant_repository.set_sms_to(tenant_id, body.sms_to)
    return SettingsResponse(sms_to=tenant.sms_to)
