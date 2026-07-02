from src.agents.agent_realty import RealtyAgent, _filter_by_criteria, _find_listing
from src.prompts.instructions import REALTOR_INSTRUCTIONS

CATALOG = [
    {"code": "RR-101", "address": "14 Zephyrwood Crescent, Sarnia", "beds": 2},
    {"code": "RR-102", "address": "88 Maple Ridge Drive, Sarnia", "beds": 3},
    {"code": "RR-103", "address": "7 Lakeshore Road, Bright's Grove", "beds": 4},
]


class _FakeApi:
    def __init__(
        self,
        answer: str = "A matching home",
        raises: bool = False,
        catalog: list[dict] | None = None,
        buyer: dict | None = None,
    ) -> None:
        self.answer = answer
        self.raises = raises
        self.catalog = catalog or []
        self.buyer = buyer or {"found": False}
        self.calls: list[tuple[str, str]] = []
        self.get_buyer_calls: list[str] = []

    async def recall(self, realtor: str, criteria: str) -> str:
        self.calls.append((realtor, criteria))
        if self.raises:
            raise RuntimeError("backend down")
        return self.answer

    async def list_listings(self) -> list[dict]:
        return self.catalog

    async def capture_lead(self, buyer: dict) -> dict:
        return {"ok": True}

    async def get_buyer(self, phone: str) -> dict:
        self.get_buyer_calls.append(phone)
        return self.buyer


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


def test_filter_by_criteria_parses_bedrooms():
    out = _filter_by_criteria(CATALOG, "3 bedroom home in Sarnia")
    assert {h["code"] for h in out} == {"RR-102", "RR-103"}  # >= 3 beds


def test_filter_by_criteria_falls_back_to_full_catalog():
    assert _filter_by_criteria(CATALOG, "all current listings") == CATALOG
    # a bed count nothing matches also falls back rather than showing nothing
    assert _filter_by_criteria(CATALOG, "9 bedroom estate") == CATALOG


def test_find_listing_by_code_then_address():
    assert _find_listing(CATALOG, "RR-102")["code"] == "RR-102"
    assert _find_listing(CATALOG, "maple ridge")["code"] == "RR-102"
    assert _find_listing(CATALOG, "nowhere at all") is None


async def test_emit_shortlist_pushes_filtered_matches(monkeypatch):
    agent = RealtyAgent(realtor="Riley", api=_FakeApi(catalog=CATALOG))
    pushed: list[tuple[str, dict]] = []

    async def fake_push(event_type: str, data: dict) -> None:
        pushed.append((event_type, data))

    monkeypatch.setattr(agent, "_push_event", fake_push)
    await agent._emit_shortlist("3 bed in Sarnia")
    assert pushed[0][0] == "shortlist"
    assert {m["code"] for m in pushed[0][1]["matches"]} == {"RR-102", "RR-103"}


async def test_push_event_is_a_noop_without_a_room():
    # No LiveKit job context in a unit test: the push resolves to nothing, never raises.
    agent = RealtyAgent(realtor="Riley", api=_FakeApi())
    await agent._push_event("shortlist", {"matches": []})


def test_persona_sets_realtor_name_and_personalizes_opener():
    agent = RealtyAgent(
        api=_FakeApi(), persona={"name": "Morgan Bell", "agency": "Bluewater Homes"}
    )
    assert agent._realtor == "Morgan Bell"  # answers in the realtor's own name
    assert "Morgan Bell's assistant at Bluewater Homes" in agent._opener()


def test_name_only_persona_opener():
    agent = RealtyAgent(api=_FakeApi(), persona={"name": "Morgan Bell"})
    assert "Morgan Bell's assistant" in agent._opener()


def test_no_persona_falls_back_to_generic_opener():
    agent = RealtyAgent(realtor="Riley", api=_FakeApi())
    assert "the realtor's assistant" in agent._opener()


async def test_sip_caller_phone_seeds_last_phone():
    # SIP caller ID is known at connect, so it is available for recall/close before any tool call.
    agent = RealtyAgent(api=_FakeApi(), caller_phone="+15195550142")
    assert agent.last_phone == "+15195550142"


async def test_recall_returning_buyer_and_opener():
    api = _FakeApi(
        buyer={"found": True, "summary": "Dana wants a 3-bed in Sarnia under 470k"}
    )
    agent = RealtyAgent(api=api, caller_phone="+15195550142")
    recalled = await agent._recall_returning_buyer()
    assert recalled and "Dana" in recalled
    assert api.get_buyer_calls == ["+15195550142"]
    opener = agent._opener(recalled)
    assert "returning caller" in opener.lower()
    assert "Dana" in opener


async def test_recall_is_once_per_call():
    api = _FakeApi(buyer={"found": True, "summary": "x"})
    agent = RealtyAgent(api=api, caller_phone="+1")
    assert await agent._recall_returning_buyer() is not None
    assert (
        await agent._recall_returning_buyer() is None
    )  # already recalled; no second lookup
    assert api.get_buyer_calls == ["+1"]


async def test_no_recall_without_a_phone():
    api = _FakeApi(buyer={"found": True, "summary": "x"})
    agent = RealtyAgent(api=api)  # web: no caller id yet
    assert await agent._recall_returning_buyer() is None
    assert api.get_buyer_calls == []


async def test_recall_degrades_when_backend_errors():
    class _Boom(_FakeApi):
        async def get_buyer(self, phone: str) -> dict:
            raise RuntimeError("backend down")

    agent = RealtyAgent(api=_Boom(), caller_phone="+1")
    assert await agent._recall_returning_buyer() is None  # never raises into the call
