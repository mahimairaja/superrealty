from contextlib import asynccontextmanager

from src.agents.call_context import CallContext
from src.agents.scheduling_agent import SchedulingAgent


class _FakeApi:
    def __init__(self, availability=None):
        self.availability = availability or {"days": []}
        self.booking_calls: list[dict] = []

    async def check_availability(self):
        return self.availability

    async def book_showing(self, booking):
        self.booking_calls.append(booking)
        return {"status": "accepted", "address": "1 Main St", "synced": True}


class _FakeCtx:
    def disallow_interruptions(self):
        pass

    def with_filler(self, *args, **kwargs):
        @asynccontextmanager
        async def _cm():
            yield

        return _cm()


_SLOTS = {
    "days": [
        {
            "date": "2026-07-08",
            "slots": [
                {"startUtc": "2026-07-08T13:00:00Z", "label": "9:00 AM"},
                {"startUtc": "2026-07-08T14:00:00Z", "label": "10:00 AM"},
            ],
        }
    ]
}


def _scheduling(api):
    return SchedulingAgent(CallContext(realtor="Riley", api=api))


async def test_check_availability_captures_offered_slots():
    agent = _scheduling(_FakeApi(availability=_SLOTS))
    out = await agent.check_availability(_FakeCtx())
    assert "9:00 AM" in out
    assert agent.ctx._offered_slots == {"2026-07-08T13:00:00Z", "2026-07-08T14:00:00Z"}


async def test_book_showing_rejects_an_unoffered_slot():
    api = _FakeApi()
    agent = _scheduling(api)
    out = await agent.book_showing(
        _FakeCtx(),
        property_code="RR-102",
        start_utc="2026-07-08T13:00:00Z",
        name="Dana",
        phone="+15195550100",
    )
    assert "open" in out.lower() or "available" in out.lower()
    assert api.booking_calls == []


async def test_book_showing_accepts_an_offered_slot(monkeypatch):
    api = _FakeApi(availability=_SLOTS)
    agent = _scheduling(api)

    async def fake_push(t, d):
        return None

    monkeypatch.setattr(agent.ctx, "push_event", fake_push)
    await agent.check_availability(_FakeCtx())
    await agent.book_showing(
        _FakeCtx(),
        property_code="RR-102",
        start_utc="2026-07-08T13:00:00Z",
        name="Dana",
        phone="+15195550100",
    )
    assert api.booking_calls
    assert api.booking_calls[0]["start"] == "2026-07-08T13:00:00Z"


async def test_to_concierge_shares_context():
    from src.agents.concierge_agent import ConciergeAgent

    agent = _scheduling(_FakeApi())
    nxt = await agent.to_concierge(_FakeCtx())
    assert isinstance(nxt, ConciergeAgent)
    assert nxt.ctx is agent.ctx
