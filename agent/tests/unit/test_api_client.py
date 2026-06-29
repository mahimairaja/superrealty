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
