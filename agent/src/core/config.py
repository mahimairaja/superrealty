import logging
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv(override=False)

logger = logging.getLogger(__name__)


class Config(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", case_sensitive=True)

    # Identity. AGENT_NAME is also the dispatch name the frontend must request.
    AGENT_NAME: str = "realty"
    ENV: str = "prod"
    PROJECT_NAME: str = "Voice Agent"

    # Hard cap on call length in seconds (cost guard for STT/LLM/TTS).
    AGENT_MAX_CALL_SECONDS: int = 600
    # Backend base URL the agent's tools call (the realty memory/recall API).
    BACKEND_URL: str = "http://localhost:8000"

    # Shared secret the agent presents (X-Agent-Secret) so the backend trusts the tenant the
    # agent asserts (X-Tenant-Id, derived from the room name). Must match the backend's
    # AGENT_SERVICE_SECRET. Without it the tenant-scoped endpoints (recall, buyers) refuse.
    AGENT_SERVICE_SECRET: str | None = None

    # Optional error tracking.
    SENTRY_DSN: str | None = None

    # NOTE: LIVEKIT_URL / LIVEKIT_API_KEY / LIVEKIT_API_SECRET and the provider
    # keys (OPENAI_API_KEY, DEEPGRAM_API_KEY, GOOGLE_API_KEY for Gemini TTS) are
    # read directly from the environment by the LiveKit framework and plugins.
    # No Config fields are needed for them.


@lru_cache
def get_config() -> Config:
    return Config()


config = get_config()
