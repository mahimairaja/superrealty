import httpx

from src.services import sms_service


async def test_send_sms_posts_telnyx_message():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = request.read().decode()
        return httpx.Response(200, json={"data": {"id": "msg_1"}})

    result = await sms_service.send_sms(
        to="+15195551111",
        text="New lead: Dana",
        api_key="k",
        from_number="+15195550000",
        transport=httpx.MockTransport(handler),
    )
    assert "api.telnyx.com/v2/messages" in seen["url"]
    assert "New lead: Dana" in seen["body"]
    assert "+15195551111" in seen["body"]
    assert result["data"]["id"] == "msg_1"
