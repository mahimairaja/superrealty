import logging
from functools import lru_cache
from urllib.parse import parse_qsl, quote_plus, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.enums import EnvironmentOption

load_dotenv(override=False)


logger = logging.getLogger(__name__)

# libpq query params that asyncpg.connect() does not accept as kwargs.
# TLS is instead enabled via connect_args (see Config.SQLALCHEMY_CONNECT_ARGS).
_LIBPQ_ONLY_PARAMS = {"sslmode", "channel_binding"}
_SSL_DISABLED = {"disable", "false", "0", "no", "off"}
_SSL_OPTIONAL = {"allow", "prefer"}

# Dev placeholder for JWT_SECRET_KEY. Production startup fails fast (see the
# Config validator) if this is left unchanged or the secret is too short.
_PLACEHOLDER_JWT_SECRET = "change-me-in-prod-change-me-in-prod-32chars-min"
_MIN_JWT_SECRET_LEN = 32


def _to_async_url(url: str) -> str:
    """Coerce a Postgres URL to the asyncpg driver and drop libpq-only query
    params (sslmode, channel_binding) that asyncpg rejects.

    Lets you paste a managed-Postgres URL (Neon/Supabase) verbatim, e.g.
    ``postgresql://u:p@host/db?sslmode=require`` ->
    ``postgresql+asyncpg://u:p@host/db``.
    """
    parts = urlsplit(url)
    base_scheme = parts.scheme.split("+", 1)[0]
    scheme = (
        "postgresql+asyncpg"
        if base_scheme in {"postgres", "postgresql"}
        else parts.scheme
    )
    query = [
        (k, v) for k, v in parse_qsl(parts.query) if k.lower() not in _LIBPQ_ONLY_PARAMS
    ]
    return urlunsplit(
        (scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )


def _url_requires_ssl(url: str) -> bool | None:
    """Infer TLS requirement from a URL's sslmode/ssl query param.

    Returns True (require/verify-*), False (disable), or None (unspecified or
    optional modes like allow/prefer).
    """
    params = {k.lower(): v.lower() for k, v in parse_qsl(urlsplit(url).query)}
    mode = params.get("sslmode") or params.get("ssl")
    if mode is None:
        return None
    if mode in _SSL_DISABLED:
        return False
    if mode in _SSL_OPTIONAL:
        return None
    return True


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    ENV: EnvironmentOption = EnvironmentOption.PROD
    DEBUG: bool | None = None

    API: str = "/api"
    API_V1_STR: str = "/api/v1"
    API_STR: str = "/api"

    MCP_STR: str = "/mcp"
    MCP_SERVER_URL: str = "http://127.0.0.1:8000/mcp"

    PROJECT_NAME: str = "Mahimai's - - -"

    # CORS: comma-separated origins. Empty means allow all ("*").
    CORS_ORIGINS_STR: str | None = ""

    # Widget guard for the public token endpoint. WIDGET_ALLOWED_ORIGINS_STR is a
    # comma-separated allowlist; empty means the guard does NOT enforce by Origin (dev),
    # which is NOT the same as CORS "*". See the WIDGET_ALLOWED_ORIGINS property.
    WIDGET_ALLOWED_ORIGINS_STR: str | None = ""
    WIDGET_TOKEN_RATELIMIT_PER_MIN: int = 20
    WIDGET_TOKEN_TTL_SECONDS: int = 300

    # Database
    DATABASE_URL: str | None = None
    DB_USER: str | None = None
    DB_HOST: str | None = None
    DB_PORT: int | None = None
    DB_NAME: str | None = None
    DB_PASSWORD: SecretStr | None = None
    DB_SSL: str | None = None
    DB_FORCE_ROLL_BACK: bool = False

    @model_validator(mode="after")
    def set_debug_default(self):
        if self.DEBUG is None:
            self.DEBUG = self.ENV == EnvironmentOption.DEV
        return self

    @model_validator(mode="after")
    def enforce_prod_secret(self):
        """Fail fast in production if the JWT secret is the placeholder or weak."""
        if self.ENV == EnvironmentOption.PROD:
            secret = self.JWT_SECRET_KEY.get_secret_value()
            if secret == _PLACEHOLDER_JWT_SECRET or len(secret) < _MIN_JWT_SECRET_LEN:
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a strong, unique value "
                    f"(>= {_MIN_JWT_SECRET_LEN} chars) when ENV=prod"
                )
        return self

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return _to_async_url(self.DATABASE_URL)

        if not all(
            [self.DB_USER, self.DB_HOST, self.DB_PORT, self.DB_NAME, self.DB_PASSWORD]
        ):
            raise ValueError(
                "Either DATABASE_URL or all DB_* fields (DB_USER, DB_HOST, DB_PORT, DB_NAME, DB_PASSWORD) must be set"
            )

        db_password = quote_plus(self.DB_PASSWORD.get_secret_value())
        return (
            f"postgresql+asyncpg://{quote_plus(self.DB_USER)}:{db_password}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def SQLALCHEMY_CONNECT_ARGS(self) -> dict[str, object]:
        # statement_cache_size=0 keeps asyncpg compatible with transaction
        # poolers (pgbouncer / Neon / Supabase pooler).
        args: dict[str, object] = {"statement_cache_size": 0}

        ssl_required: bool | None = None
        if self.DB_SSL:
            ssl_required = self.DB_SSL.strip().lower() not in _SSL_DISABLED
        elif self.DATABASE_URL:
            ssl_required = _url_requires_ssl(self.DATABASE_URL)

        if ssl_required is True:
            args["ssl"] = True
        elif ssl_required is False:
            args["ssl"] = False

        return args

    @property
    def BACKEND_CORS_ORIGINS(self) -> list[str]:
        # Derived at runtime from the resolved CORS_ORIGINS_STR (not at class
        # definition time). Empty/unset means allow all.
        origins = [
            o.strip() for o in (self.CORS_ORIGINS_STR or "").split(",") if o.strip()
        ]
        return origins or ["*"]

    @property
    def WIDGET_ALLOWED_ORIGINS(self) -> list[str]:
        # Empty means the widget guard does not enforce by Origin (dev). Unlike
        # BACKEND_CORS_ORIGINS, an empty list here does NOT become "*". Blank/whitespace
        # entries are dropped so a malformed value never yields a bogus empty origin.
        return [
            o.strip()
            for o in (self.WIDGET_ALLOWED_ORIGINS_STR or "").split(",")
            if o.strip()
        ]

    JWT_SECRET_KEY: SecretStr = SecretStr(_PLACEHOLDER_JWT_SECRET)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ---- LiveKit (room token minting) -------------------------------------
    # Required by POST /api/v1/token. The backend signs room tokens with the
    # same key/secret the agent worker uses, so they MUST match the agent's.
    LIVEKIT_URL: str | None = None
    LIVEKIT_API_KEY: str | None = None
    LIVEKIT_API_SECRET: SecretStr | None = None

    # VoiceGateway usage widget: the vk_ ingest key (the same key the agent +
    # backend telemetry use) mints a per-realtor embed token so a realtor sees
    # their own call usage on the Overview. Empty -> the widget endpoint 503s.
    VOICEGW_API_KEY: SecretStr | None = None
    VOICEGW_CLOUD_API: str = "https://cloud-api-production-dc6e.up.railway.app"

    # Shared secret the agent worker presents (X-Agent-Secret) so the backend can trust the
    # tenant it asserts (X-Tenant-Id). Must match the agent's AGENT_SERVICE_SECRET. Without
    # it, the tenant-scoped agent endpoints refuse, so a forged header cannot cross tenants.
    AGENT_SERVICE_SECRET: SecretStr | None = None

    # cal.com booking (the realtor's showing calendar). Without these, availability and
    # bookings degrade to a spoken fallback. RR_CAL_EVENT_TYPE_ID is the new showings event.
    CAL_API_KEY: SecretStr | None = None
    RR_CAL_EVENT_TYPE_ID: int | None = None
    CAL_DEFAULT_TIMEZONE: str = "America/Toronto"

    # Telnyx SMS: the post-call lead handoff to the realtor. Without all three, no SMS.
    TELNYX_API_KEY: SecretStr | None = None
    TELNYX_FROM_NUMBER: str | None = None
    REALTOR_SMS_TO: str | None = None

    # ---- Clerk auth (multi-tenant SaaS) -----------------------------------
    # The realtor console authenticates with Clerk; tenant = Clerk organization.
    # CLERK_ISSUER is the instance URL, e.g. https://your-app.clerk.accounts.dev
    # (its /.well-known/jwks.json verifies session tokens). The public buyer call
    # widget stays unauthenticated.
    CLERK_SECRET_KEY: SecretStr | None = None
    CLERK_PUBLISHABLE_KEY: str | None = None
    CLERK_ISSUER: str | None = None
    CLERK_JWKS_URL_OVERRIDE: str | None = None

    @property
    def CLERK_JWKS_URL(self) -> str | None:
        if self.CLERK_JWKS_URL_OVERRIDE:
            return self.CLERK_JWKS_URL_OVERRIDE
        if self.CLERK_ISSUER:
            return self.CLERK_ISSUER.rstrip("/") + "/.well-known/jwks.json"
        return None

    @field_validator("RR_CAL_EVENT_TYPE_ID", mode="before")
    @classmethod
    def _blank_int_to_none(cls, v: object) -> object:
        # Empty env values (e.g. RR_CAL_EVENT_TYPE_ID=) are common; treat as unset.
        return None if v in ("", None) else v

    # find query
    PAGE: int = 1
    PAGE_SIZE: int = 10
    ORDERING: str = "-id"


@lru_cache
def get_config() -> Config:
    return Config()


config = get_config()
