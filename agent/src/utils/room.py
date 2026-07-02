import json
import logging
from dataclasses import dataclass

from livekit import rtc

logger = logging.getLogger(__name__)


@dataclass
class Caller:
    """A connected participant, classified by transport."""

    kind: str  # "web" or "sip"
    identity: str
    phone: str | None = None


def parse_tenant_id(room_name: str | None) -> str | None:
    """Recover the tenant_id from a ``t_{tenant_id}_{random}`` room name, or None.

    The backend mints the room name and encodes the realtor's tenant (their Clerk org id)
    into it. The org id itself contains underscores, and the random suffix is uuid hex with
    none, so the tenant is everything between the ``t_`` prefix and the LAST underscore.
    This MUST match the backend's tenant_from_room_name codec.
    """
    if not room_name or not room_name.startswith("t_"):
        return None
    tenant_id, _, suffix = room_name[2:].rpartition("_")
    if not tenant_id or not suffix:
        return None
    return tenant_id


def parse_room_metadata(raw: str | None) -> dict:
    """Safely parse room metadata as JSON; return {} on any failure."""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        logger.warning("Room metadata is not valid JSON: %r", raw)
        return {}


def tenant_from_metadata(raw: str | None) -> str | None:
    """Recover the tenant_id from metadata JSON ({"tenant_id": "..."}), or None.

    Used for callers whose room name cannot carry the tenant: SIP dispatch passes it as agent
    job metadata (roomConfig.agents[].metadata), and direct LiveKit dispatchers that name their
    own room pass it as room metadata (ctx.room.metadata).
    """
    value = parse_room_metadata(raw).get("tenant_id")
    return value if isinstance(value, str) and value else None


def resolve_tenant_id(
    room_name: str | None,
    job_metadata: str | None,
    room_metadata: str | None,
) -> str | None:
    """Recover the call's tenant_id from whichever carrier the dispatcher used, or None.

    Precedence (the carriers are mutually exclusive in practice):
    1. the backend-minted room name ``t_{tenant}_{random}`` (web and console calls),
    2. agent job metadata (the SIP dispatch rule sets roomConfig.agents[].metadata),
    3. LiveKit room metadata, for a dispatcher that names its own room and passes
       ``{"tenant_id": "..."}`` as room metadata (e.g. Cekura's LiveKit v2 test runs).
    """
    return (
        parse_tenant_id(room_name)
        or tenant_from_metadata(job_metadata)
        or tenant_from_metadata(room_metadata)
    )


def identify(participant: rtc.Participant) -> Caller:
    """Classify a participant as a web or SIP caller.

    SIP participants report a SIP participant kind and carry the originating
    number in the ``sip.phoneNumber`` attribute.
    """
    attrs = participant.attributes or {}
    phone = attrs.get("sip.phoneNumber") or None
    is_sip = participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP or bool(phone)
    return Caller(
        kind="sip" if is_sip else "web",
        identity=participant.identity,
        phone=phone if is_sip else None,
    )
