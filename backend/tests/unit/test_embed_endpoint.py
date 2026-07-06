import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

import src.api.endpoints.embed as embed_mod
from src.api.endpoints.embed import router as embed_router
from src.core.clerk import get_tenant_id


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(embed_router, prefix="/api/v1")
    # Skip real Clerk auth: the authenticated realtor is a fixed org.
    app.dependency_overrides[get_tenant_id] = lambda: "org_realtor_1"
    return app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=_app()), base_url="http://test"
    ) as c:
        yield c


async def test_returns_503_when_key_unset(client, monkeypatch):
    monkeypatch.setattr(embed_mod.config, "VOICEGW_API_KEY", None)
    resp = await client.get("/api/v1/embed/token")
    assert resp.status_code == 503


async def test_mints_token_scoped_to_the_authenticated_realtor(client, monkeypatch):
    monkeypatch.setattr(embed_mod.config, "VOICEGW_API_KEY", SecretStr("vk_test"))

    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {"token": "tok1", "expires_at": 999}

    class _MockClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            # the vk_ key is forwarded server-side, scoped to the realtor's own sub
            assert headers["Authorization"] == "Bearer vk_test"
            assert json["subtenant"] == "org_realtor_1"
            return _Resp()

    monkeypatch.setattr(embed_mod.httpx, "AsyncClient", _MockClient)
    resp = await client.get("/api/v1/embed/token")
    assert resp.status_code == 200
    assert resp.json() == {"token": "tok1", "expires_at": 999}
