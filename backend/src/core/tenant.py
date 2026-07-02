"""Tenant routing helpers shared by the token mint, the call-close path, and the agent.

A LiveKit room name encodes the tenant as ``t_{tenant_id}_{random}``. tenant_id is the
Clerk organization id, which itself contains underscores (e.g. ``org_2ab...``), so decoding
strips the ``t_`` prefix and splits the trailing random suffix off the RIGHT. The random
suffix is uuid hex (no underscores), so the rpartition is unambiguous.
"""

from __future__ import annotations

import hmac
import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from src.core.config import config


def room_name_for_tenant(tenant_id: str) -> str:
    """Encode a tenant into a fresh room name."""
    return f"t_{tenant_id}_{uuid.uuid4().hex[:12]}"


def tenant_from_room_name(room: str | None) -> str | None:
    """Recover the tenant_id from a ``t_{tenant_id}_{random}`` room name, or None."""
    if not room or not room.startswith("t_"):
        return None
    tenant_id, _, suffix = room[2:].rpartition("_")
    if not tenant_id or not suffix:
        return None
    return tenant_id


def has_valid_agent_secret(x_agent_secret: str | None) -> bool:
    """True when the presented secret matches the configured AGENT_SERVICE_SECRET.

    Identifies the trusted first-party voice worker in constant time. Shared by the agent
    tenant gate and the widget guard so both recognize the agent by the same rule. Returns
    False when the secret is unconfigured or absent, so it never accidentally trusts a caller.
    """
    expected = (
        config.AGENT_SERVICE_SECRET.get_secret_value()
        if config.AGENT_SERVICE_SECRET
        else None
    )
    return bool(
        expected and x_agent_secret and hmac.compare_digest(x_agent_secret, expected)
    )


async def get_agent_tenant_id(
    x_tenant_id: Annotated[str, Header(alias="X-Tenant-Id")],
    x_agent_secret: Annotated[str | None, Header(alias="X-Agent-Secret")] = None,
) -> str:
    """Agent requests carry the tenant in the X-Tenant-Id header (the agent derives it by
    parsing its room name). The realtor console uses get_current_tenant (Clerk JWT) instead.

    The header is self-asserted, so it is only trusted when the caller also presents the
    shared agent secret (X-Agent-Secret == AGENT_SERVICE_SECRET). Without that gate any
    client could forge a tenant id and poison another realtor's memory or book on their
    calendar. The secret must be configured; if it is unset the endpoint refuses outright.
    """
    if not has_valid_agent_secret(x_agent_secret):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="agent service authentication required",
        )
    if not x_tenant_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-Id header is required",
        )
    return x_tenant_id


# Terse alias for agent-facing route signatures (recall, buyers, matches), mirroring
# clerk.CurrentTenant for the console. The agent presents X-Tenant-Id + X-Agent-Secret.
AgentTenant = Annotated[str, Depends(get_agent_tenant_id)]
