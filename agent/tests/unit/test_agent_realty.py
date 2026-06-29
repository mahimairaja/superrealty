from src.agents.agent_realty import RealtyAgent
from src.prompts.instructions import REALTOR_INSTRUCTIONS


class _FakeApi:
    def __init__(self, answer: str = "A matching home", raises: bool = False) -> None:
        self.answer = answer
        self.raises = raises
        self.calls: list[tuple[str, str]] = []

    async def recall(self, realtor: str, criteria: str) -> str:
        self.calls.append((realtor, criteria))
        if self.raises:
            raise RuntimeError("backend down")
        return self.answer


def test_instructions_cover_disclosure_and_qualification():
    text = REALTOR_INSTRUCTIONS.lower()
    assert "record" in text  # recording disclosure
    assert "budget" in text
    assert "timeline" in text
    assert "financing" in text
    assert "area" in text
    assert "only" in text  # only the realtor's connected listings


async def test_search_delegates_to_backend():
    api = _FakeApi(answer="A 3 bed bungalow at 123 Maple")
    agent = RealtyAgent(realtor="Riley", api=api)
    out = await agent._search("3 bed in Sarnia")
    assert out == "A 3 bed bungalow at 123 Maple"
    assert api.calls == [("Riley", "3 bed in Sarnia")]


async def test_search_degrades_on_backend_error():
    agent = RealtyAgent(realtor="Riley", api=_FakeApi(raises=True))
    out = await agent._search("anything")
    assert "trouble" in out.lower()
