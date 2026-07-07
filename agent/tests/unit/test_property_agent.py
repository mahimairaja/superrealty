from src.agents.call_context import CallContext
from src.agents.listing_filters import ListingSearchFilters
from src.agents.property_agent import (
    PropertyAgent,
    _find_listing,
    _format_listings_answer,
)

CATALOG = [
    {"code": "RR-101", "address": "14 Zephyrwood Crescent, Sarnia", "beds": 2},
    {"code": "RR-102", "address": "88 Maple Ridge Drive, Sarnia", "beds": 3},
    {"code": "RR-103", "address": "7 Lakeshore Road, Bright's Grove", "beds": 4},
]


class _FakeApi:
    def __init__(self, catalog=None):
        self.catalog = catalog or []

    async def list_listings(self):
        return self.catalog


class _Ctx:
    pass


def _property(api):
    return PropertyAgent(CallContext(realtor="Riley", api=api))


async def test_listings_answer_is_grounded_and_never_recalls():
    api = _FakeApi(
        catalog=[
            {
                "code": "RR-102",
                "address": "88 Maple Ridge Drive, Sarnia",
                "beds": 3,
                "price": 615000,
            },
            {
                "code": "RR-103",
                "address": "7 Lakeshore Road, Bright's Grove",
                "beds": 4,
                "price": 799000,
            },
        ]
    )
    agent = _property(api)
    out = await agent._listings_answer(ListingSearchFilters(min_beds=3, area="Sarnia"))
    assert "88 Maple Ridge Drive, Sarnia" in out
    assert "$615,000" in out


async def test_listings_answer_degrades_without_a_catalog():
    agent = _property(_FakeApi(catalog=[]))
    out = await agent._listings_answer(ListingSearchFilters())
    assert "trouble" in out.lower()


def test_format_listings_answer_counts_prices_and_overflow():
    homes = [
        {"address": f"{i} Main St", "beds": 3, "price": 500000 + i} for i in range(7)
    ]
    out = _format_listings_answer(homes, total=7)
    assert out.startswith("I have 7 listings")
    assert "$500,000" in out
    assert "all 7 on your screen" in out


def test_format_listings_answer_subset_missing_price_and_empty():
    one = [{"address": "1 Oak Ave", "beds": 3, "price": None}]
    assert "I found one that fits" in _format_listings_answer(one, total=9)
    assert "price on request" in _format_listings_answer(one, total=9)
    assert "follow up" in _format_listings_answer([], total=9).lower()


def test_find_listing_by_code_then_address():
    assert _find_listing(CATALOG, "RR-102")["code"] == "RR-102"
    assert _find_listing(CATALOG, "maple ridge")["code"] == "RR-102"
    assert _find_listing(CATALOG, "nowhere at all") is None


async def test_search_listings_emits_a_shortlist(monkeypatch):
    agent = _property(_FakeApi(catalog=CATALOG))
    pushed: list = []

    async def fake_push(t, d):
        pushed.append((t, d))

    monkeypatch.setattr(agent.ctx, "push_event", fake_push)
    await agent.search_listings(_Ctx(), min_beds=3)
    # search fires emit_shortlist in the background; let it run.
    import asyncio

    await asyncio.sleep(0)
    assert pushed and pushed[0][0] == "shortlist"


async def test_show_home_pushes_a_property_card(monkeypatch):
    agent = _property(_FakeApi(catalog=CATALOG))
    pushed: list = []

    async def fake_push(t, d):
        pushed.append((t, d))

    monkeypatch.setattr(agent.ctx, "push_event", fake_push)
    out = await agent.show_home(_Ctx(), home="RR-102")
    import asyncio

    await asyncio.sleep(0)
    assert "88 Maple Ridge Drive, Sarnia" in out
    assert pushed and pushed[0][0] == "property"


async def test_to_scheduling_and_to_concierge_share_context():
    from src.agents.scheduling_agent import SchedulingAgent

    from src.agents.concierge_agent import ConciergeAgent

    agent = _property(_FakeApi())
    assert isinstance(await agent.to_scheduling(_Ctx()), SchedulingAgent)
    assert isinstance(await agent.to_concierge(_Ctx()), ConciergeAgent)
    assert (await agent.to_scheduling(_Ctx())).ctx is agent.ctx
