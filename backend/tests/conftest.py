import os

# Run the test suite in dev mode so importing config does not trip the
# production JWT-secret check. Must be set before any src.* import.
os.environ.setdefault("ENV", "dev")

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from src.api.endpoints.health import router as health_router  # noqa: E402
from src.core.config import config as _config  # noqa: E402


@pytest.fixture(autouse=True)
def _disable_telnyx_by_default(monkeypatch):
    """Keep tests hermetic: a developer's local .env may configure Telnyx, which would make the
    lead-SMS path fire (and, now that it resolves a per-tenant number, hit the database). Tests
    that exercise the SMS explicitly re-enable it."""
    monkeypatch.setattr(_config, "TELNYX_API_KEY", None, raising=False)
    monkeypatch.setattr(_config, "TELNYX_FROM_NUMBER", None, raising=False)
    monkeypatch.setattr(_config, "REALTOR_SMS_TO", None, raising=False)


@pytest.fixture
def test_app():
    """Create a lightweight FastAPI app for testing (no DI, no DB)."""
    app = FastAPI()
    app.include_router(health_router)
    return app


@pytest.fixture
async def async_client(test_app):
    """Create an async test client."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
