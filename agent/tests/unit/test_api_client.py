import httpx

import src.services.api_client as api_client_mod
from src.services.api_client import BackendApiClient


async def test_tenant_and_agent_secret_headers_are_sent(monkeypatch):
    # The agent presents its tenant (from the room name) and the shared secret so the
    # backend's tenant-scoped endpoints (recall, buyers) trust the asserted tenant.
    monkeypatch.setattr(api_client_mod.config, "AGENT_SERVICE_SECRET", "s3cret")
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["tenant"] = request.headers.get("X-Tenant-Id")
        seen["secret"] = request.headers.get("X-Agent-Secret")
        return httpx.Response(200, json={"answer": "ok", "match_count": 0})

    client = BackendApiClient(
        base_url="http://test",
        transport=httpx.MockTransport(handler),
        tenant_id="org_abc",
    )
    await client.recall("Riley", "3 bed")
    assert seen == {"tenant": "org_abc", "secret": "s3cret"}


async def test_no_tenant_header_when_tenant_absent():
    # With no tenant (e.g. a demo room), the X-Tenant-Id header is simply omitted.
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["tenant"] = request.headers.get("X-Tenant-Id")
        return httpx.Response(200, json={"answer": "ok", "match_count": 0})

    client = BackendApiClient(
        base_url="http://test", transport=httpx.MockTransport(handler)
    )
    await client.recall("Riley", "3 bed")
    assert seen["tenant"] is None


async def test_recall_posts_and_returns_answer():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = request.read().decode()
        return httpx.Response(
            200,
            json={
                "realtor": "Riley",
                "answer": "A 3 bed bungalow at 1 Main St, Sarnia",
                "match_count": 1,
            },
        )

    client = BackendApiClient(
        base_url="http://test", transport=httpx.MockTransport(handler)
    )
    answer = await client.recall("Riley", "3 bed in Sarnia")
    assert seen["path"] == "/api/v1/recall"
    assert "3 bed" in answer
    assert "Riley" in seen["body"]


async def test_get_realtor_fetches_persona():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["method"] = request.method
        seen["path"] = request.url.path
        return httpx.Response(
            200,
            json={
                "name": "Morgan Bell",
                "agency": "Bluewater Homes",
                "area": "Sarnia",
                "tagline": "Homes with heart",
                "tone": "warm, local",
            },
        )

    client = BackendApiClient(
        base_url="http://test", transport=httpx.MockTransport(handler)
    )
    persona = await client.get_realtor()
    assert (seen["method"], seen["path"]) == ("GET", "/api/v1/realtor")
    assert persona["name"] == "Morgan Bell"
    assert persona["tone"] == "warm, local"


async def test_get_buyer_url_encodes_the_phone():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["raw_path"] = request.url.raw_path.decode()
        return httpx.Response(200, json={"found": False})

    client = BackendApiClient(
        base_url="http://test", transport=httpx.MockTransport(handler)
    )
    # A slash-bearing value must be encoded, not create extra path segments (no traversal).
    await client.get_buyer("+1/../admin")
    assert "/api/v1/buyers/" in seen["raw_path"]
    assert (
        "%2F" in seen["raw_path"]
        and "/admin" not in seen["raw_path"].split("/api/v1/buyers/")[1]
    )


async def test_lead_availability_booking_routes():
    seen: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.method, request.url.path))
        if request.url.path == "/api/v1/buyers":
            return httpx.Response(201, json={"phone": "+15195550100", "name": "Dana"})
        if request.url.path == "/api/v1/availability":
            return httpx.Response(
                200,
                json={
                    "timezone": "America/Toronto",
                    "days": [
                        {
                            "date": "2026-07-01",
                            "slots": [
                                {"startUtc": "2026-07-01T13:00:00Z", "label": "9:00 AM"}
                            ],
                        }
                    ],
                },
            )
        if request.url.path == "/api/v1/bookings":
            return httpx.Response(
                201,
                json={
                    "id": 1,
                    "idempotency_key": "k",
                    "status": "accepted",
                    "cal_uid": "c1",
                    "synced": True,
                },
            )
        if request.method == "DELETE" and request.url.path.startswith(
            "/api/v1/buyers/"
        ):
            return httpx.Response(200, json={"forgotten": True})
        if request.url.path.endswith("/close"):
            return httpx.Response(200, json={"id": 9, "room_name": "r"})
        return httpx.Response(404)

    client = BackendApiClient(
        base_url="http://test", transport=httpx.MockTransport(handler)
    )
    lead = await client.capture_lead({"phone": "+15195550100", "name": "Dana"})
    assert lead["name"] == "Dana"
    avail = await client.check_availability()
    assert avail["days"][0]["date"] == "2026-07-01"
    booking = await client.book_showing(
        {"idempotency_key": "k", "property_code": "L1", "start": "x", "phone": "p"}
    )
    assert booking["status"] == "accepted"
    forgot = await client.forget_buyer("+15195550100")
    assert forgot["forgotten"] is True
    closed = await client.close_call("room-1", {"outcome": "completed"})
    assert closed["id"] == 9
    assert ("POST", "/api/v1/buyers") in seen
    assert ("GET", "/api/v1/availability") in seen
    assert ("POST", "/api/v1/bookings") in seen
    assert ("DELETE", "/api/v1/buyers/+15195550100") in seen
    assert ("POST", "/api/v1/calls/room-1/close") in seen
