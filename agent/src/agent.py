import logging
import os
import sys

import sentry_sdk
from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    TurnHandlingOptions,
    cli,
)
from livekit.plugins import cartesia, deepgram, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from src.agents.agent_realty import RealtyAgent
from src.core.config import config
from src.core.events import register_event_handlers
from src.runtime.observers import post_call_log
from src.utils.room import identify, parse_tenant_id

logger = logging.getLogger("agent")

CONSOLE_MODE = "console" in sys.argv

# Quiet noisy third-party loggers.
for _noisy in ("livekit.plugins", "livekit.turn_detector", "asyncio"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

if config.SENTRY_DSN:
    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        traces_sample_rate=0.2,
        environment=os.getenv("FLY_APP_NAME", "development"),
    )

server = AgentServer(drain_timeout=300, shutdown_process_timeout=30)


def prewarm(proc: JobProcess) -> None:
    # Load the VAD once per process; shared across all sessions.
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name=config.AGENT_NAME)
async def entrypoint(ctx: JobContext) -> None:
    ctx.log_context_fields = {"room": ctx.room.name}
    await ctx.connect()

    # Recover the realtor (tenant) this call belongs to from the backend-minted room name
    # (t_{tenant}_{random}). Every memory read/write is then scoped to this realtor.
    tenant_id = parse_tenant_id(ctx.room.name)
    if tenant_id:
        ctx.log_context_fields["tenant"] = tenant_id
    else:
        logger.warning(
            "room %s has no tenant; memory tools will be unavailable", ctx.room.name
        )

    # Identify the caller. Web and SIP differ only here; the conversation is
    # identical. Skipped in console mode (local mic, no remote participant).
    if not CONSOLE_MODE:
        participant = await ctx.wait_for_participant()
        caller = identify(participant)
        logger.info(
            "participant joined: kind=%s identity=%s", caller.kind, caller.identity
        )

    session: AgentSession = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4.1-mini"),
        tts=cartesia.TTS(),
        vad=ctx.proc.userdata["vad"],
        turn_handling=TurnHandlingOptions(
            turn_detection=MultilingualModel(),
            interruption={"mode": "vad"},
        ),
    )

    realty_agent = RealtyAgent(tenant_id=tenant_id)
    log_usage_summary = register_event_handlers(session)

    async def _on_shutdown() -> None:
        log_usage_summary()
        # Persist the call log and fold the conversation into permanent memory.
        await post_call_log(
            realty_agent._api,
            ctx.room.name,
            buyer_phone=realty_agent.last_phone,
        )

    ctx.add_shutdown_callback(_on_shutdown)

    await session.start(agent=realty_agent, room=ctx.room)
    # Opt-in web mic cleanup: `uv add livekit-plugins-noise-cancellation`, then
    # pass `room_input_options=RoomInputOptions(noise_cancellation=BVC())` above
    # (import: `from livekit.agents import RoomInputOptions`,
    # `from livekit.plugins import noise_cancellation`; use `noise_cancellation.BVC()`).


if __name__ == "__main__":
    cli.run_app(server)
