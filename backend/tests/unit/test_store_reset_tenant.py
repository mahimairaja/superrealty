import src.memory.store as store_mod


async def _noop(*args, **kwargs):
    return None


class _FakeGraph:
    def __init__(self, nodes):
        self._nodes = nodes
        self.deleted: list[str] | None = None
        self.subgraph_args: dict | None = None

    async def get_nodeset_subgraph(self, node_type, node_name, **kwargs):
        self.subgraph_args = {"node_type": node_type, "node_name": node_name}
        return self._nodes, []

    async def delete_nodes(self, node_ids):
        self.deleted = node_ids


def _patch(monkeypatch, graph):
    monkeypatch.setattr(store_mod, "ensure_cognee", _noop, raising=True)

    async def fake_engine():
        return graph

    monkeypatch.setattr(store_mod, "get_graph_engine", fake_engine, raising=True)


async def test_reset_tenant_deletes_only_its_nodeset_nodes(monkeypatch):
    # Every node read back from the tenant's own subgraph is deleted, nothing else.
    graph = _FakeGraph([("n1", {"type": "Listing"}), ("n2", {"type": "Buyer"})])
    _patch(monkeypatch, graph)

    removed = await store_mod.get_memory_store().reset_tenant("org_abc")

    assert removed == 2
    assert graph.deleted == ["n1", "n2"]
    # The read is scoped to this tenant's NodeSet, so no other realtor's nodes are in scope.
    assert graph.subgraph_args["node_name"] == [store_mod.tenant_tag("org_abc")]


async def test_reset_tenant_on_empty_graph_is_a_noop(monkeypatch):
    graph = _FakeGraph([])
    _patch(monkeypatch, graph)

    removed = await store_mod.get_memory_store().reset_tenant("org_abc")

    assert removed == 0
    # No delete call is issued when there is nothing to remove.
    assert graph.deleted is None
