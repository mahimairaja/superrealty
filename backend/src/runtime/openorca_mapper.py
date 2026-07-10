"""Map the live-call registry into the openorca-ui runtime snapshot shape.

Pure and unit-testable: given a list of CallState and a timestamp, return the OpenOrcaSnapshot
dict (ClawOrchestratorData + meta) the openorca-ui NetworkCanvas renders. Each live call is one
"machine" holding three agent nodes; the active specialist glows, handoff edges become
collaboratingWith links. RealtyRecall models no tasks, actions, interventions, or swarms.
"""

from __future__ import annotations

from src.runtime.live_agents import AGENTS, CallState

# Display + domain per specialist. Domains map to openorca-ui's AgentDomain palette so the three
# nodes are visually distinct.
_LABELS = {"concierge": "Concierge", "property": "Property", "scheduling": "Scheduling"}
_DOMAINS = {
    "concierge": "communications",
    "property": "research",
    "scheduling": "productivity",
}


def _node(call: CallState, agent: str) -> dict:
    node_id = f"{call.room}:{agent}"
    is_active = agent == call.active
    neighbors = {b if a == agent else a for (a, b) in call.edges if agent in (a, b)}
    return {
        "id": node_id,
        "name": _LABELS[agent],
        "machineId": f"call:{call.room}",
        "machineName": "Live call",
        "status": "active" if is_active else "idle",
        "domain": _DOMAINS[agent],
        "integrations": [],
        "currentTaskId": None,
        "currentAction": call.action if is_active else "",
        "memoryUsage": 0,
        "uptime": "",
        "tasksCompleted": 0,
        "collaboratingWith": sorted(f"{call.room}:{n}" for n in neighbors),
        "interventionRequired": False,
        "activityLevel": 1.0 if is_active else 0.0,
        "loadedCores": [],
        "knowledgeContributions": 0,
        "graphAccess": "read",
    }


def to_snapshot(calls: list[CallState], generated_at: str) -> dict:
    machines = [
        {
            "id": f"call:{c.room}",
            "name": "Live call",
            "os": "linux",
            "isOnline": True,
            "lastSeen": generated_at,
        }
        for c in calls
    ]
    agents = [_node(c, a) for c in calls for a in AGENTS]
    fleet = {
        "totalAgents": len(calls) * len(AGENTS),
        "activeAgents": len(calls),
        "offlineAgents": 0,
        "interventionsRequired": 0,
        "tasksInProgress": len(calls),
        "tasksCompletedToday": 0,
        "swarmsActive": 0,
        "overallHealth": "healthy",
    }
    return {
        "machines": machines,
        "agents": agents,
        "tasks": [],
        "actionLog": [],
        "interventions": [],
        "swarms": [],
        "fleetHealth": fleet,
        "meta": {
            "runtime": "realtyrecall",
            "runtimeVersion": "1",
            "generatedAt": generated_at,
            "connectionStatus": "connected",
        },
    }
