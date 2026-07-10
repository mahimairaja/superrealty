import asyncio

from src.runtime.live_agents import AGENTS, LiveAgentRegistry


def test_update_creates_a_call_starting_active():
    reg = LiveAgentRegistry()
    state = reg.update("org_a", "t_org_a_1", active="concierge", action="Greeting")
    assert state.active == "concierge"
    assert state.action == "Greeting"
    assert state.edges == set()
    assert [c.room for c in reg.snapshot_calls("org_a")] == ["t_org_a_1"]


def test_update_records_a_handoff_edge():
    reg = LiveAgentRegistry()
    reg.update("org_a", "t_org_a_1", active="concierge", action="Greeting")
    reg.update(
        "org_a",
        "t_org_a_1",
        active="property",
        action="Searching",
        from_agent="concierge",
    )
    state = reg.snapshot_calls("org_a")[0]
    assert state.active == "property"
    assert ("concierge", "property") in state.edges


def test_snapshot_is_tenant_scoped():
    reg = LiveAgentRegistry()
    reg.update("org_a", "t_org_a_1", active="concierge", action="Greeting")
    reg.update("org_b", "t_org_b_1", active="concierge", action="Greeting")
    assert [c.room for c in reg.snapshot_calls("org_a")] == ["t_org_a_1"]
    assert [c.room for c in reg.snapshot_calls("org_b")] == ["t_org_b_1"]


def test_ttl_sweep_drops_a_stale_call():
    clock = {"t": 1000.0}
    reg = LiveAgentRegistry(now=lambda: clock["t"], ttl=600.0)
    reg.update("org_a", "t_org_a_1", active="concierge", action="Greeting")
    clock["t"] = 1000.0 + 601.0
    assert reg.snapshot_calls("org_a") == []


def test_agents_constant_is_the_three_specialists():
    assert AGENTS == ("concierge", "property", "scheduling")


async def test_publish_reaches_a_subscriber():
    reg = LiveAgentRegistry()
    q = reg.subscribe("org_a")
    await reg.publish("org_a", {"hello": "world"})
    assert await asyncio.wait_for(q.get(), timeout=1) == {"hello": "world"}
    reg.unsubscribe("org_a", q)


async def test_publish_does_not_cross_tenants():
    reg = LiveAgentRegistry()
    qa = reg.subscribe("org_a")
    qb = reg.subscribe("org_b")
    await reg.publish("org_a", {"for": "a"})
    assert qa.qsize() == 1
    assert qb.qsize() == 0
