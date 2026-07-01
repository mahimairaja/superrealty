"""The in-memory staging store (the tests/local default; the DB store mirrors its behavior)."""

from src.services.onboard_service import InMemoryStagingStore

T = "org_store_test"


async def test_stage_assigns_ids_and_lists_back():
    store = InMemoryStagingStore()
    out = await store.stage(T, [{"address": "1 A St"}, {"address": "2 B St"}])
    assert all(d["id"] for d in out)
    listed = await store.list(T)
    assert {d["address"] for d in listed} == {"1 A St", "2 B St"}


async def test_patch_updates_only_non_none_fields():
    store = InMemoryStagingStore()
    (draft,) = await store.stage(T, [{"address": "1 A St", "price": 100}])
    updated = await store.patch(T, draft["id"], {"price": 200, "address": None})
    assert updated is not None
    assert updated["price"] == 200
    assert updated["address"] == "1 A St"  # None change is ignored
    assert await store.patch(T, "missing", {"price": 9}) is None


async def test_remove_and_clear():
    store = InMemoryStagingStore()
    (draft,) = await store.stage(T, [{"address": "1 A St"}])
    assert await store.remove(T, draft["id"]) is True
    assert await store.remove(T, draft["id"]) is False
    await store.stage(T, [{"address": "2 B St"}])
    await store.clear(T)
    assert await store.list(T) == []


async def test_profile_roundtrip_and_scoping():
    store = InMemoryStagingStore()
    await store.stage_profile(T, {"name": "Riley"})
    assert (await store.get_profile(T))["name"] == "Riley"
    await store.stage_profile(
        T, None
    )  # a profile-less onboard does not wipe an existing one
    assert (await store.get_profile(T))["name"] == "Riley"
    assert await store.get_profile("org_other") is None
    await store.clear()
    assert await store.get_profile(T) is None
