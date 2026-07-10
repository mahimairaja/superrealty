from datetime import datetime

from src.agents.call_context import CONCIERGE, CallContext
from src.agents.listing_filters import ListingSearchFilters


class _FakeApi:
    def __init__(self, catalog=None, profile=None, raises=False):
        self.catalog = catalog or []
        self.profile = profile or {"found": False}
        self.raises = raises
        self.get_buyer_profile_calls: list[str] = []

    async def list_listings(self):
        return self.catalog

    async def get_buyer_profile(self, phone):
        self.get_buyer_profile_calls.append(phone)
        if self.raises:
            raise RuntimeError("backend down")
        return self.profile


CATALOG = [
    {"code": "RR-101", "address": "14 Zephyrwood Crescent, Sarnia", "beds": 2},
    {"code": "RR-102", "address": "88 Maple Ridge Drive, Sarnia", "beds": 3},
]


def test_defaults_start_on_the_concierge():
    ctx = CallContext(api=_FakeApi())
    assert ctx.active == CONCIERGE
    assert ctx.resolved is False
    assert ctx.room is None


def test_who_uses_persona_name_and_agency():
    ctx = CallContext(
        api=_FakeApi(), persona={"name": "Morgan Bell", "agency": "Bluewater Homes"}
    )
    assert ctx.who() == "Morgan Bell's assistant at Bluewater Homes"


def test_who_falls_back_to_generic():
    assert CallContext(api=_FakeApi()).who() == "the realtor's assistant"


def test_opener_personalizes_and_welcomes_returning_buyer():
    ctx = CallContext(api=_FakeApi(), persona={"name": "Morgan Bell"})
    assert "Morgan Bell's assistant" in ctx.opener()
    back = ctx.opener("Dana. 3+ beds under $470,000")
    assert "returning caller" in back.lower()
    assert "Dana" in back


def test_today_line_states_the_year():
    line = CallContext(api=_FakeApi()).today_line()
    assert "today is" in line.lower()
    assert str(datetime.now().year) in line


def test_today_line_survives_a_bad_timezone(monkeypatch):
    import src.agents.call_context as m

    monkeypatch.setattr(m.config, "TIMEZONE", "Not/AZone")
    assert "today is" in CallContext(api=_FakeApi()).today_line().lower()


async def test_recall_returning_buyer_reads_the_fast_profile():
    api = _FakeApi(
        profile={
            "found": True,
            "name": "Dana",
            "prefs_summary": "3+ beds, under $470,000",
        }
    )
    ctx = CallContext(api=api, caller_phone="+15195550142")
    recalled = await ctx.recall_returning_buyer()
    assert recalled and "Dana" in recalled and "3+ beds" in recalled
    assert api.get_buyer_profile_calls == ["+15195550142"]


async def test_recall_is_once_per_call():
    api = _FakeApi(profile={"found": True, "name": "Dana"})
    ctx = CallContext(api=api, caller_phone="+15195550142")
    assert await ctx.recall_returning_buyer() is not None
    assert await ctx.recall_returning_buyer() is None
    assert api.get_buyer_profile_calls == ["+15195550142"]


async def test_recall_rejects_a_non_phone():
    api = _FakeApi(profile={"found": True, "name": "Dana"})
    for bad in ("../admin", "abc", "12", "+1"):
        ctx = CallContext(api=api, caller_phone=bad)
        assert await ctx.recall_returning_buyer() is None
    assert api.get_buyer_profile_calls == []


async def test_recall_degrades_when_backend_errors():
    ctx = CallContext(api=_FakeApi(raises=True), caller_phone="+15195550142")
    assert await ctx.recall_returning_buyer() is None


async def test_push_event_is_a_noop_without_a_room():
    await CallContext(api=_FakeApi()).push_event("shortlist", {"matches": []})


async def test_emit_shortlist_pushes_filtered_matches(monkeypatch):
    ctx = CallContext(api=_FakeApi(catalog=CATALOG))
    pushed: list[tuple[str, dict]] = []

    async def fake_push(event_type, data):
        pushed.append((event_type, data))

    monkeypatch.setattr(ctx, "push_event", fake_push)
    await ctx.emit_shortlist(ListingSearchFilters(min_beds=3))
    assert pushed[0][0] == "shortlist"
    assert {m["code"] for m in pushed[0][1]["matches"]} == {"RR-102"}


async def test_report_state_sets_active_and_is_a_noop_without_a_room():
    # No room set yet: report_state records the active agent locally but never calls the backend.
    ctx = CallContext(api=_FakeApi())
    ctx.report_state("property", "Searching homes")
    assert ctx.active == "property"


async def test_report_state_fires_the_intake_best_effort(monkeypatch):
    sent: list[dict] = []

    class _ReportingApi(_FakeApi):
        async def report_agent_state(self, room, active, action, from_agent=None):
            sent.append(
                {"room": room, "active": active, "action": action, "from": from_agent}
            )

    ctx = CallContext(api=_ReportingApi())
    ctx.room = "t_org_1_abc"
    ctx.report_state("scheduling", "Checking the calendar", from_agent="property")
    # fire() schedules a task; let it run.
    import asyncio

    await asyncio.sleep(0)
    assert ctx.active == "scheduling"
    assert sent == [
        {
            "room": "t_org_1_abc",
            "active": "scheduling",
            "action": "Checking the calendar",
            "from": "property",
        }
    ]


async def test_report_state_never_raises_when_the_backend_errors():
    class _BrokenApi(_FakeApi):
        async def report_agent_state(self, room, active, action, from_agent=None):
            raise RuntimeError("backend down")

    ctx = CallContext(api=_BrokenApi())
    ctx.room = "t_org_1_abc"
    ctx.report_state("property", "Searching homes")  # must not raise
    import asyncio

    await asyncio.sleep(0)


async def test_close_runs_teardown_exactly_once(monkeypatch):
    import src.agents.call_context as m

    closed: list[str] = []
    logged: list[bool] = []

    class _ClosingApi(_FakeApi):
        async def aclose(self):
            closed.append("aclose")

    async def fake_post_call_log(api, room, buyer_phone=None):
        logged.append(True)

    monkeypatch.setattr(m, "post_call_log", fake_post_call_log)
    ctx = CallContext(api=_ClosingApi())
    ctx.room = "t_org_1_abc"
    await ctx.close()
    await ctx.close()  # second call is a no-op
    assert closed == ["aclose"]
    assert logged == [True]
