"""Mint a VoiceGateway embed token for the per-realtor usage widget.

A realtor's browser must never see the vk_ ingest key, so the frontend calls
this proxy. It mints a short-lived embed token scoped to the AUTHENTICATED
realtor's own sub-tenant (their Clerk org), so a realtor can only ever see
their own call usage. The widget iframe then reads the token.
"""

from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.core.clerk import get_tenant_id
from src.core.config import config

router = APIRouter(prefix="/embed", tags=["embed"])

# VoiceGateway caps the TTL at its own embed_token_max_ttl (24h); ask for that.
_TOKEN_TTL_SECONDS = 86_400


class EmbedTokenResponse(BaseModel):
    token: str
    expires_at: int


@router.get("/token", response_model=EmbedTokenResponse)
async def mint_embed_token(
    tenant_id: Annotated[str, Depends(get_tenant_id)],
) -> EmbedTokenResponse:
    """Return a fresh VoiceGateway embed token scoped to the caller's realtor."""
    key = config.VOICEGW_API_KEY
    if key is None or not key.get_secret_value():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "usage widget not configured"
        )
    url = f"{config.VOICEGW_CLOUD_API.rstrip('/')}/v1/embed/token"
    headers = {"Authorization": f"Bearer {key.get_secret_value()}"}
    payload = {"subtenant": tenant_id, "ttl_seconds": _TOKEN_TTL_SECONDS}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "voicegateway unreachable"
        ) from exc
    if resp.status_code != 200:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"mint failed ({resp.status_code})"
        )
    data = resp.json()
    return EmbedTokenResponse(token=data["token"], expires_at=data["expires_at"])
