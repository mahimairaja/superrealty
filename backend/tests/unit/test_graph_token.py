import time

import jwt
import pytest
from fastapi import HTTPException

from src.core.graph_token import mint_graph_token, verify_graph_token


def test_round_trip_returns_the_tenant():
    token = mint_graph_token("org_a")
    assert verify_graph_token(token) == "org_a"


def test_rejects_a_tampered_token():
    with pytest.raises(HTTPException) as exc:
        verify_graph_token("not-a-jwt")
    assert exc.value.status_code == 401


def test_rejects_an_expired_token():
    # Mint an already-expired token directly with the same secret: PyJWT's default exp check
    # must reject it (faking the clock is harder than backdating the exp claim).
    import src.core.graph_token as m

    secret = m.config.JWT_SECRET_KEY.get_secret_value()
    expired = jwt.encode(
        {"tid": "org_a", "scope": "openorca", "exp": int(time.time()) - 10},
        secret,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        verify_graph_token(expired)
    assert exc.value.status_code == 401


def test_rejects_a_wrong_scope_token():
    import src.core.graph_token as m

    secret = m.config.JWT_SECRET_KEY.get_secret_value()
    other = jwt.encode(
        {"tid": "org_a", "scope": "something-else", "exp": int(time.time()) + 60},
        secret,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        verify_graph_token(other)
    assert exc.value.status_code == 401
