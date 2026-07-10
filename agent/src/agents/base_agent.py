"""Shared plumbing for the three call specialists.

Each specialist holds one shared CallContext and reports its activity to the live graph on
entry. A handoff is a @function_tool that returns the next Agent (built on the same context);
LiveKit swaps current_agent and runs the new agent's on_enter.
"""

from __future__ import annotations

import logging

from livekit.agents import Agent

from src.agents.call_context import CallContext

logger = logging.getLogger("agent")


class RealtyBaseAgent(Agent):
    ID: str = ""  # graph-node id; set by each subclass
    ACTION: str = ""  # short currentAction shown on the node

    def __init__(self, ctx: CallContext, instructions: str) -> None:
        self.ctx = ctx
        super().__init__(instructions=instructions)

    @property
    def _tenant_id(self) -> str | None:
        # traced_tool reads self._tenant_id for the log/breadcrumb tenant; the tenant lives on
        # the shared context now, so expose it here.
        return self.ctx.tenant_id

    async def on_enter(self) -> None:
        # Report this specialist as the active node (best-effort; never blocks the turn).
        self.ctx.report_state(self.ID, self.ACTION)

    def _handoff(self, agent: RealtyBaseAgent) -> RealtyBaseAgent:
        """Report the handoff edge (this -> next) and return the next agent for LiveKit to run."""
        self.ctx.report_state(agent.ID, agent.ACTION, from_agent=self.ID)
        return agent
