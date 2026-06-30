from datetime import datetime

from sqlalchemy import DateTime
from sqlmodel import Field

from src.models.base_model import BaseModel


class Booking(BaseModel, table=True):
    """Operational booking row. The Showing graph node lives in Cognee; this row is the
    idempotent, cal.com-synced record of a confirmed showing on the realtor's calendar.
    """

    __tablename__ = "bookings"

    tenant_id: str | None = Field(default=None, index=True)
    idempotency_key: str = Field(index=True, unique=True, nullable=False)
    room_name: str | None = Field(default=None, index=True)
    property_code: str | None = Field(default=None)
    address: str | None = Field(default=None)
    start_utc: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    timezone: str | None = Field(default=None)
    status: str = Field(default="pending", nullable=False)
    cal_uid: str | None = Field(default=None, index=True)
    synced: bool = Field(default=False, nullable=False)
    attendee_name: str | None = Field(default=None)
    attendee_email: str | None = Field(default=None)
    phone: str | None = Field(default=None, index=True)
