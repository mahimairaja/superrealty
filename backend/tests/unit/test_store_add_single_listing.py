import src.memory.store as store_mod
from src.memory.models import Listing, Neighbourhood, Realtor


async def _noop(*args, **kwargs):
    return None


def _patch(monkeypatch, captured):
    async def fake_add_points(points):
        captured["points"] = points

    monkeypatch.setattr(store_mod, "ensure_cognee", _noop, raising=True)
    monkeypatch.setattr(store_mod, "add_data_points", fake_add_points, raising=True)


async def test_add_single_listing_tags_nodeset_and_shares_neighbourhood(monkeypatch):
    captured: dict = {}
    _patch(monkeypatch, captured)

    await store_mod.get_memory_store().add_single_listing(
        "org_abc",
        {
            "code": "RR-201",
            "address": "9 Marina View Terrace",
            "beds": 3,
            "area": "Sarnia",
        },
    )

    listing = next(p for p in captured["points"] if isinstance(p, Listing))
    assert listing.code == "RR-201"
    # Tagged with the tenant NodeSet so buyer-match search finds it.
    assert [ns.id for ns in listing.belongs_to_set] == [
        store_mod._tenant_nodeset("org_abc").id
    ]
    # Linked to the SAME stable neighbourhood node the realtor's other listings use.
    assert isinstance(listing.located_in, Neighbourhood)
    assert listing.located_in.id == store_mod._neighbourhood("org_abc", "Sarnia").id
    # A manual add never spawns a duplicate Realtor node.
    assert not any(isinstance(p, Realtor) for p in captured["points"])


async def test_add_single_listing_without_area_has_no_neighbourhood(monkeypatch):
    captured: dict = {}
    _patch(monkeypatch, captured)

    await store_mod.get_memory_store().add_single_listing(
        "org_abc", {"code": "RR-202", "address": "5 Nowhere Lane"}
    )

    listing = next(p for p in captured["points"] if isinstance(p, Listing))
    assert listing.located_in is None
    assert not any(isinstance(p, Neighbourhood) for p in captured["points"])
