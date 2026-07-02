import re

from pydantic import BaseModel, field_validator

_PHONE = re.compile(r"^\+?[0-9][0-9\s\-().]{5,}$")


class SettingsUpdate(BaseModel):
    sms_to: str | None = None

    @field_validator("sms_to")
    @classmethod
    def _validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if not _PHONE.match(trimmed):
            raise ValueError("enter a valid phone number, e.g. +15195550142")
        return trimmed


class SettingsResponse(BaseModel):
    sms_to: str | None = None
