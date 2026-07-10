from src.runtime.live_agents import CallState
from src.runtime.openorca_mapper import to_snapshot


def _call(room="t_org_a_1", active="property", edges=None):
    return CallState(
        tenant_id="org_a",
        room=room,
        active=active,
        action="Searching listings",
        edges=edges or {("concierge", "property")},
        started_at=0.0,
        updated_at=0.0,
    )


def test_snapshot_has_the_openorca_top_level_shape():
    snap = to_snapshot([_call()], generated_at="2026-07-07T00:00:00Z")
    for key in (
        "machines",
        "agents",
        "tasks",
        "actionLog",
        "interventions",
        "swarms",
        "fleetHealth",
        "meta",
    ):
        assert key in snap
    assert snap["tasks"] == []
    assert snap["interventions"] == []
    assert snap["meta"]["runtime"] == "realtyrecall"
    assert snap["meta"]["generatedAt"] == "2026-07-07T00:00:00Z"
    assert snap["meta"]["connectionStatus"] == "connected"


def test_each_call_yields_three_nodes_with_one_active():
    snap = to_snapshot([_call(active="property")], generated_at="t")
    agents = snap["agents"]
    assert len(agents) == 3
    by_id = {a["id"]: a for a in agents}
    assert by_id["t_org_a_1:property"]["status"] == "active"
    assert by_id["t_org_a_1:property"]["currentAction"] == "Searching listings"
    assert by_id["t_org_a_1:concierge"]["status"] == "idle"
    assert by_id["t_org_a_1:concierge"]["currentAction"] == ""


def test_edges_render_as_collaborating_with():
    snap = to_snapshot([_call(edges={("concierge", "property")})], generated_at="t")
    by_id = {a["id"]: a for a in snap["agents"]}
    assert "t_org_a_1:property" in by_id["t_org_a_1:concierge"]["collaboratingWith"]
    assert "t_org_a_1:concierge" in by_id["t_org_a_1:property"]["collaboratingWith"]


def test_nodes_group_under_one_machine_per_call():
    snap = to_snapshot([_call(room="t_org_a_1")], generated_at="t")
    assert [m["id"] for m in snap["machines"]] == ["call:t_org_a_1"]
    assert all(a["machineId"] == "call:t_org_a_1" for a in snap["agents"])


def test_fleet_health_counts_active_calls():
    snap = to_snapshot([_call(), _call(room="t_org_a_2")], generated_at="t")
    fh = snap["fleetHealth"]
    assert fh["totalAgents"] == 6
    assert fh["activeAgents"] == 2
    assert fh["tasksInProgress"] == 2
    assert fh["overallHealth"] == "healthy"


def test_empty_snapshot_is_valid():
    snap = to_snapshot([], generated_at="t")
    assert snap["agents"] == []
    assert snap["machines"] == []
    assert snap["fleetHealth"]["totalAgents"] == 0
