import src.memory.store as store_mod
from src.memory.models import Buyer, Neighbourhood


async def _noop(*args, **kwargs):
    return None


def _patch(monkeypatch, captured):
    async def fake_add_points(points):
        captured["points"] = points

    monkeypatch.setattr(store_mod, "ensure_cognee", _noop, raising=True)
    monkeypatch.setattr(store_mod, "add_data_points", fake_add_points, raising=True)
    monkeypatch.setattr(store_mod.cognee, "add", _noop, raising=True)
    monkeypatch.setattr(store_mod.cognee, "cognify", _noop, raising=True)


async def test_upsert_buyer_links_to_the_neighbourhood_by_area(monkeypatch):
    # A remembered buyer with a stated area is attached to the neighbourhood node, so the buyer
    # joins the graph instead of floating disconnected.
    captured: dict = {}
    _patch(monkeypatch, captured)
    await store_mod.get_memory_store().upsert_buyer(
        "org_abc",
        {"phone": "+15195550142", "name": "Dana", "criteria": {"area": "Sarnia"}},
    )
    buyer = next(p for p in captured["points"] if isinstance(p, Buyer))
    assert isinstance(buyer.wants_in, Neighbourhood)
    assert buyer.wants_in.name == "Sarnia"
    # The same stable node the realtor's listings connect to (id derived from tenant + name).
    assert buyer.wants_in.id == store_mod._neighbourhood("org_abc", "Sarnia").id


async def test_upsert_buyer_without_an_area_has_no_neighbourhood(monkeypatch):
    captured: dict = {}
    _patch(monkeypatch, captured)
    await store_mod.get_memory_store().upsert_buyer(
        "org_abc", {"phone": "+15195550142", "name": "Dana", "criteria": {}}
    )
    buyer = next(p for p in captured["points"] if isinstance(p, Buyer))
    assert buyer.wants_in is None
    assert not any(isinstance(p, Neighbourhood) for p in captured["points"])


def test_neighbourhood_node_is_stable_and_area_name_is_normalized():
    # Listings and buyers in the same area must resolve to one node, case- and space-insensitive.
    a = store_mod._neighbourhood("org_abc", "Sarnia")
    b = store_mod._neighbourhood("org_abc", " sarnia ")
    assert a.id == b.id
    # A different tenant gets a different node (isolation).
    assert store_mod._neighbourhood("org_xyz", "Sarnia").id != a.id
