# backend/tests/unit/test_graph_service.py
import pytest

import src.memory.graph_service as gs


class _FakeGraph:
    def __init__(self, nodes, edges):
        self._nodes = nodes
        self._edges = edges

    async def get_nodeset_subgraph(self, node_type, node_name):
        return self._nodes, self._edges


@pytest.fixture(autouse=True)
def _no_cognee(monkeypatch):
    # get_subgraph must not require a live Cognee; stub setup + the graph engine.
    async def _noop():
        return None

    monkeypatch.setattr(gs, "ensure_cognee", _noop, raising=True)


async def test_get_subgraph_shapes_nodes_and_edges(monkeypatch):
    nodes = [
        (
            "11111111-1111-1111-1111-111111111111",
            {
                "type": "Listing",
                "code": "RR-102",
                "address": "88 Maple Ridge Drive, Sarnia",
            },
        ),
        (
            "22222222-2222-2222-2222-222222222222",
            {"type": "Buyer", "name": "Dana Callahan", "phone": "+15195550142"},
        ),
    ]
    edges = [
        (
            "22222222-2222-2222-2222-222222222222",
            "11111111-1111-1111-1111-111111111111",
            "wants",
            {},
        ),
    ]

    async def _fake_engine():
        return _FakeGraph(nodes, edges)

    monkeypatch.setattr(gs, "get_graph_engine", _fake_engine, raising=True)

    out = await gs.get_graph_service().get_subgraph("org_abc")
    assert {n["type"] for n in out["nodes"]} == {"Listing", "Buyer"}
    listing = next(n for n in out["nodes"] if n["type"] == "Listing")
    assert (
        listing["label"] == "88 Maple Ridge Drive, Sarnia"
    )  # address wins as the label
    buyer = next(n for n in out["nodes"] if n["type"] == "Buyer")
    assert buyer["label"] == "Dana Callahan"  # name wins for a buyer
    assert out["edges"] == [
        {
            "source": "22222222-2222-2222-2222-222222222222",
            "target": "11111111-1111-1111-1111-111111111111",
            "rel": "wants",
        }
    ]


async def test_get_subgraph_caps_nodes(monkeypatch):
    nodes = [
        (str(i), {"type": "Listing", "address": f"{i} Main St"}) for i in range(200)
    ]

    async def _fake_engine():
        return _FakeGraph(nodes, [])

    monkeypatch.setattr(gs, "get_graph_engine", _fake_engine, raising=True)
    out = await gs.get_graph_service().get_subgraph("org_abc", cap=150)
    assert len(out["nodes"]) == 150
    # edges referencing dropped nodes are removed so the render never dangles
    assert out["edges"] == []


async def test_get_subgraph_keeps_the_most_recent_nodes_when_capping(monkeypatch):
    # created_at ascending by index; with cap=2 the two NEWEST (highest created_at) survive.
    nodes = [
        (
            str(i),
            {
                "type": "Listing",
                "address": f"{i} Main St",
                "created_at": f"2026-07-0{i}",
            },
        )
        for i in range(1, 5)
    ]

    async def _fake_engine():
        return _FakeGraph(nodes, [])

    monkeypatch.setattr(gs, "get_graph_engine", _fake_engine, raising=True)
    out = await gs.get_graph_service().get_subgraph("org_abc", cap=2)
    labels = {n["label"] for n in out["nodes"]}
    assert labels == {"4 Main St", "3 Main St"}  # newest two, not the oldest two
