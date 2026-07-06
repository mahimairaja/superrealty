"""Boot smoke: the agent module imports and builds its openrtc pool without a
microphone, a LiveKit connection, or per-session provider init. Per-call setup
(tenant, persona, caller, telemetry) now happens in RealtyAgent.on_enter.
"""

import src.agent as agent_module
from src.agents.agent_realty import RealtyAgent


def test_agent_boots_as_realty():
    assert agent_module.config.AGENT_NAME == "realty"


def test_build_pool_constructs_without_livekit():
    # Building the pool wires the shared providers + registers the realty agent;
    # it must not need a mic, a LiveKit connection, or an event loop.
    pool = agent_module.build_pool()
    assert pool is not None


def test_realty_agent_is_arglessly_constructible():
    # The AgentPool constructs one RealtyAgent per call with no arguments; the
    # per-call context is filled in on_enter. So an arg-less construction must work.
    agent = RealtyAgent()
    assert agent is not None
    # on_enter / on_exit are the per-call lifecycle hooks the pool drives.
    assert hasattr(agent, "on_enter") and hasattr(agent, "on_exit")


def test_container_entrypoint_imports_and_uses_build_pool():
    # The Docker image runs the agent via ``main.py`` (download-files at build,
    # start at run). The openrtc migration replaced the module-level ``server``
    # with ``build_pool()``; if main.py still imported the old symbol the image
    # would fail to build AND start. Import it here so that regression is caught
    # without a container. The ``if __name__ == "__main__"`` guard keeps the
    # import side-effect-free (no cli.run_app on import).
    import main

    assert main.build_pool is agent_module.build_pool
