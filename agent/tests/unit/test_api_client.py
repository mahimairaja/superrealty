import httpx

from src.services.api_client import BackendApiClient


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
