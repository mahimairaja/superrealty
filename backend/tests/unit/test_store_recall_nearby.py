import src.memory.store as store_mod


async def test_recall_nearby_returns_a_suggestion(monkeypatch):
    async def _noop():
        return None

    async def fake_search(**kwargs):
        assert kwargs["query_type"] is store_mod.SearchType.GRAPH_COMPLETION
        assert kwargs["node_name"] == ["tenant_org_abc"]
        return [
            "A new 3-bed on Cathcart Boulevard just came up near the water you liked."
        ]

    monkeypatch.setattr(store_mod, "ensure_cognee", _noop, raising=True)
    monkeypatch.setattr(store_mod.cognee, "search", fake_search, raising=True)
    out = await store_mod.get_memory_store().recall_nearby(
        "org_abc", "Dana liked a bungalow near the water in Sarnia."
    )
    assert "Cathcart" in out


async def test_recall_nearby_never_raises(monkeypatch):
    async def _noop():
        return None

    async def boom(**kwargs):
        raise RuntimeError("graph down")

    monkeypatch.setattr(store_mod, "ensure_cognee", _noop, raising=True)
    monkeypatch.setattr(store_mod.cognee, "search", boom, raising=True)
    assert await store_mod.get_memory_store().recall_nearby("org_abc", "x") is None


async def test_recall_nearby_returns_none_when_setup_fails(monkeypatch):
    async def boom_setup():
        raise RuntimeError("cognee down")

    monkeypatch.setattr(store_mod, "ensure_cognee", boom_setup, raising=True)
    assert await store_mod.get_memory_store().recall_nearby("org_abc", "x") is None
