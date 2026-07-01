from src.services import llm_service


async def test_llm_degrades_without_an_api_key(monkeypatch):
    # No key configured -> the client is never built and extraction degrades to empty/None,
    # so onboarding still works from structured data alone.
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(llm_service, "_client", None)
    assert await llm_service.extract_listings("Home for $459,000, 3 bed") == []
    assert await llm_service.synthesize_profile("Riley Realty in Sarnia") is None
