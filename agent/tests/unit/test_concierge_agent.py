from src.agents.call_context import CallContext
from src.agents.concierge_agent import ConciergeAgent


class _FakeApi:
    def __init__(self, buyer_profile=None):
        self.buyer_profile = buyer_profile or {"found": False}
        self.captured: list[dict] = []
        self.forgot: list[str] = []

    async def capture_lead(self, buyer):
        self.captured.append(buyer)
        return {"ok": True}

    async def get_buyer_profile(self, phone):
        return self.buyer_profile

    async def forget_buyer(self, phone):
        self.forgot.append(phone)
        return {"ok": True}


class _Ctx:
    """A RunContext stand-in (concierge tools do not use it)."""


def _concierge(api, **ctx_kwargs):
    return ConciergeAgent(CallContext(api=api, **ctx_kwargs))


def test_concierge_node_identity():
    agent = _concierge(_FakeApi())
    assert agent.ID == "concierge"


async def test_capture_lead_records_and_seeds_phone(monkeypatch):
    api = _FakeApi()
    agent = _concierge(api)
    monkeypatch.setattr(agent.ctx, "push_event", _noop_push)
    out = await agent.capture_lead(
        _Ctx(),
        name="Dana",
        phone="+15195550100",
        area="Sarnia",
        max_price=470000,
        min_beds=3,
    )
    assert agent.ctx.last_phone == "+15195550100"
    assert api.captured and api.captured[0]["name"] == "Dana"
    assert api.captured[0]["criteria"] == {
        "area": "Sarnia",
        "maxPrice": 470000,
        "minBeds": 3,
    }
    assert "Dana" in out


async def test_capture_lead_welcomes_a_returning_buyer(monkeypatch):
    api = _FakeApi(
        buyer_profile={"found": True, "name": "Dana", "prefs_summary": "3+ beds"}
    )
    agent = _concierge(api)
    monkeypatch.setattr(agent.ctx, "push_event", _noop_push)
    out = await agent.capture_lead(_Ctx(), name="Dana", phone="+15195550100")
    assert "returning buyer" in out.lower()
    assert "3+ beds" in out


async def test_forget_me_requires_a_known_phone():
    agent = _concierge(_FakeApi())
    out = await agent.forget_me(_Ctx())
    assert "phone number" in out.lower()


async def test_forget_me_forgets_the_captured_caller():
    api = _FakeApi()
    agent = _concierge(api, caller_phone="+15195550100")
    out = await agent.forget_me(_Ctx())
    assert api.forgot == ["+15195550100"]
    assert agent.ctx.last_phone is None
    assert "removed" in out.lower()


async def test_to_property_hands_off_on_the_same_context():
    from src.agents.property_agent import PropertyAgent

    agent = _concierge(_FakeApi())
    nxt = await agent.to_property(_Ctx())
    assert isinstance(nxt, PropertyAgent)
    assert nxt.ctx is agent.ctx  # shared state survives the handoff


async def test_to_scheduling_hands_off_on_the_same_context():
    from src.agents.scheduling_agent import SchedulingAgent

    agent = _concierge(_FakeApi())
    nxt = await agent.to_scheduling(_Ctx())
    assert isinstance(nxt, SchedulingAgent)
    assert nxt.ctx is agent.ctx


async def _noop_push(event_type, data):
    return None
