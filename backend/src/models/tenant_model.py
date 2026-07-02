from sqlmodel import Field

from src.models.base_model import BaseModel


class Tenant(BaseModel, table=True):
    """A realtor account. One tenant maps to one Clerk organization; `clerk_org_id`
    is the tenant boundary. Operational rows carry `tenant_id = clerk_org_id`, and
    Cognee datasets are namespaced `tenant_{clerk_org_id}_...`.
    """

    __tablename__ = "tenants"

    clerk_org_id: str = Field(index=True, unique=True, nullable=False)
    name: str | None = Field(default=None)
    plan: str = Field(default="free", nullable=False)
    # Where the realtor wants post-call lead texts. Per tenant, so each realtor is notified at
    # their own number; falls back to the global REALTOR_SMS_TO when unset (single-realtor demo).
    sms_to: str | None = Field(default=None)
