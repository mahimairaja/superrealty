import logging
import os
from typing import Literal

import sentry_sdk
from livekit.plugins import deepgram, openai
from livekit.plugins.turn_detector.multilingual import (  # noqa: F401 (openrtc shared prewarm)
    MultilingualModel,
)
from openrtc import AgentPool

from src.agents.agent_realty import RealtyAgent
from src.core.config import config

logger = logging.getLogger("agent")

# Quiet noisy third-party loggers.
for _noisy in ("livekit.plugins", "livekit.turn_detector", "asyncio"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

if config.SENTRY_DSN:
    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        traces_sample_rate=0.2,
        environment=os.getenv("FLY_APP_NAME", "development"),
    )


def _isolation() -> Literal["coroutine", "process"]:
    """AgentPool isolation from AGENT_ISOLATION, narrowed to the accepted literals.

    Defaults to coroutine (one worker, many concurrent calls as asyncio tasks);
    only an explicit AGENT_ISOLATION=process opts into per-call process isolation.
    Any other value falls back to coroutine rather than reaching AgentPool as a
    bare str (which the type checker rejects).
    """
    return "process" if os.getenv("AGENT_ISOLATION") == "process" else "coroutine"


def build_pool() -> AgentPool:
    """Construct the openrtc pool that hosts RealtyAgent.

    One worker runs many concurrent calls as asyncio tasks (coroutine isolation),
    lifting the box from a handful of calls to ~50. openrtc shares one Silero VAD +
    turn detector across every session (prewarmed once per worker), so the per-call
    setup that used to live in the entrypoint now runs in RealtyAgent.on_enter
    (post-connect, where the participant and room are available). Set
    AGENT_ISOLATION=process for hard per-call crash isolation.
    """
    pool = AgentPool(
        default_stt=deepgram.STT(model="nova-3"),
        default_llm=openai.LLM(model="gpt-4.1-mini"),
        # Deepgram Aura TTS reads DEEPGRAM_API_KEY, the same funded key as the STT.
        default_tts=deepgram.TTS(model="aura-2-thalia-en"),
        isolation=_isolation(),
        max_concurrent_sessions=int(os.getenv("AGENT_MAX_CONCURRENT_SESSIONS", "50")),
        drain_timeout=300,
        # openrtc "top": per-call memory / CPU / event-loop-block attribution, so a
        # slow Cognee query starving the shared loop is visible per session.
        enable_introspection=True,
        slow_session_threshold_ms=50.0,
        # Hot reload for dev only (edit RealtyAgent instructions/tools, swap live
        # calls on their next turn). Off in prod: a redeploy is the prod path.
        enable_hot_reload=os.getenv("AGENT_HOT_RELOAD") == "1",
        # Blue-green: tag the pool with the deploy version so a rollout lets
        # in-flight buyer calls finish on the old version (drain_timeout=300).
        deployment_version=(
            os.getenv("AGENT_DEPLOYMENT_VERSION")
            or os.getenv("RAILWAY_GIT_COMMIT_SHA")
            or None
        ),
        # Per-tenant provider config / caps / circuit breaker are intentionally
        # NOT set: openrtc keys those on the dispatch ``tenant`` metadata, which
        # RealtyRecall does not emit today (the realtor is in the room NAME,
        # t_{tenant}_{random}). Enabling the breaker without it would key every
        # call to "default" and could trip the whole fleet on a transient blip.
        # Per-tenant provider tiers also assume a static tenant set, which does
        # not fit dynamic realtors. See LOOP_PROGRESS for the follow-up.
    )
    # greeting=None: on_enter owns the opening reply (recording disclosure + the
    # realtor's persona + returning-caller recall). One agent, addressed by the
    # worker's agent_name; the room name carries the realtor (tenant).
    pool.add(config.AGENT_NAME, RealtyAgent, greeting=None)
    return pool


if __name__ == "__main__":
    build_pool().run()
