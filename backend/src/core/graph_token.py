"""Short-lived signed token that authorizes a realtor's browser to read its own live agent
graph.

openorca-ui fetches the snapshot/events URLs with a plain fetch() and EventSource, neither of
which can carry a Clerk bearer header, so the console mints this token (Clerk-authed) and the
browser passes it in the ?token= query string. The token is HMAC-signed with JWT_SECRET_KEY,
scoped to "openorca", short-lived, and carries only the tenant id, so it grants nothing beyond
reading that tenant's graph.
"""

from __future__ import annotations

import time
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Query, status

from src.core.config import config

GRAPH_TOKEN_TTL_SECONDS = 3600
_SCOPE = "openorca"


def mint_graph_token(tenant_id: str) -> str:
    secret = config.JWT_SECRET_KEY.get_secret_value()
    return jwt.encode(
        {
            "tid": tenant_id,
            "scope": _SCOPE,
            "exp": int(time.time()) + GRAPH_TOKEN_TTL_SECONDS,
        },
        secret,
        algorithm="HS256",
    )


def verify_graph_token(token: str) -> str:
    secret = config.JWT_SECRET_KEY.get_secret_value()
    try:
        claims = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="invalid graph token"
        ) from exc
    if claims.get("scope") != _SCOPE or not claims.get("tid"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid graph token")
    return str(claims["tid"])


async def openorca_tenant(token: Annotated[str, Query()]) -> str:
    """Resolve the tenant from the ?token= graph token on the openorca read endpoints."""
    return verify_graph_token(token)


OpenOrcaTenant = Annotated[str, Depends(openorca_tenant)]
