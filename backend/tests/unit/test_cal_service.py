import httpx

from src.services import cal_service


async def test_get_available_slots_parses_days():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/slots"
        assert request.url.params["eventTypeId"] == "123"
        return httpx.Response(
            200,
            json={"data": {"2026-07-01": [{"start": "2026-07-01T13:00:00.000Z"}]}},
        )

    days = await cal_service.get_available_slots(
        event_type_id=123,
        api_key="k",
        timezone="America/Toronto",
        transport=httpx.MockTransport(handler),
    )
    assert days[0]["date"] == "2026-07-01"
    assert days[0]["slots"][0]["startUtc"] == "2026-07-01T13:00:00Z"
    assert days[0]["slots"][0]["label"]


async def test_create_showing_booking_posts_request_and_parses():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["body"] = request.read().decode()
        return httpx.Response(
            201,
            json={
                "data": {
                    "uid": "bk_1",
                    "status": "accepted",
                    "start": "2026-07-01T13:00:00Z",
                    "end": "2026-07-01T13:15:00Z",
                    "references": [{"type": "google_calendar"}],
                }
            },
        )

    out = await cal_service.create_showing_booking(
        event_type_id=123,
        start_utc_iso="2026-07-01T13:00:00Z",
        attendee_name="Dana",
        attendee_phone="+15195550100",
        attendee_timezone="America/Toronto",
        property_address="123 Maple St, Sarnia",
        api_key="k",
        transport=httpx.MockTransport(handler),
    )
    assert seen["path"] == "/v2/bookings"
    assert "123 Maple St, Sarnia" in seen["body"]
    # The event type has no `property-address` field; sending one makes cal.com reject the
    # whole booking. The address must ride in `notes` instead.
    assert "property-address" not in seen["body"]
    assert out["uid"] == "bk_1"
    assert out["status"] == "accepted"
    assert out["synced"] is True


async def test_create_showing_booking_normalizes_phone_to_e164():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = request.read().decode()
        return httpx.Response(
            201, json={"data": {"uid": "b", "status": "accepted", "start": "s"}}
        )

    await cal_service.create_showing_booking(
        event_type_id=1,
        start_utc_iso="2026-07-01T13:00:00Z",
        attendee_name="Dana",
        attendee_phone="5195550100",  # bare 10-digit, as a web caller enters it
        attendee_timezone="America/Toronto",
        property_address="1 A St",
        api_key="k",
        transport=httpx.MockTransport(handler),
    )
    assert "+15195550100" in seen["body"]


def test_to_e164():
    assert cal_service._to_e164("5195550100") == "+15195550100"
    assert cal_service._to_e164("(519) 555-0100") == "+15195550100"
    assert cal_service._to_e164("15195550100") == "+15195550100"
    assert cal_service._to_e164("+15195550100") == "+15195550100"
