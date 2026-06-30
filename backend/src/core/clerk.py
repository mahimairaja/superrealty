"""Clerk authentication for the multi-tenant SaaS.

Verifies a Clerk session JWT against Clerk's JWKS and resolves the tenant from the
token's active organization (`org_id`). The public buyer call widget stays
unauthenticated; these dependencies guard the realtor console only.
"""

import logging
from typing import Annotated, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

from src.core.config import config

logger = logging.getLogger(__name__)

clerk_scheme = HTTPBearer(auto_error=True)

_jwks_client: jwt.PyJWKClient | None = None


def _get_jwks_client() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not config.CLERK_JWKS_URL:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Clerk auth is not configured (set CLERK_ISSUER)",
            )
        _jwks_client = jwt.PyJWKClient(config.CLERK_JWKS_URL)
    return _jwks_client


def verify_clerk_token(token: str) -> dict[str, Any]:
    """Verify a Clerk session JWT (RS256, JWKS-signed) and return its claims."""
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Clerk token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_tenant_id(
    credentials: Annotated[Any, Depends(clerk_scheme)],
) -> str:
    """FastAPI dependency: the verified tenant id (Clerk organization id)."""
    claims = verify_clerk_token(credentials.credentials)
    # Clerk puts the active org in `org_id` (default JWT template) or `o.id` (newer).
    org_id = claims.get("org_id")
    if not org_id and isinstance(claims.get("o"), dict):
        org_id = claims["o"].get("id")
    if not org_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="No active organization in the session; select or create one",
        )
    return str(org_id)
