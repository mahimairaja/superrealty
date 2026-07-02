"""Widget guard for the public token endpoint.

An Origin allowlist plus a per-IP rate limit bound the casual abuse and cost of the
PUBLIC token endpoint. They are NOT strong authentication and do NOT lock the widget to a
specific embedding site (that needs per-site keys, deferred). A server-side caller can
forge the Origin header; real browsers cannot. The limiter is per-process (single warm
backend today); multi-worker accuracy would need a shared store.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from fastapi import HTTPException, Request, status

from src.core.config import get_config
from src.core.tenant import has_valid_agent_secret


class RateLimiter:
    """Per-key sliding-window limiter. Uses a monotonic clock so the window is immune to
    wall-clock/NTP jumps; the clock is injectable for deterministic tests.
    """

    def __init__(
        self, max_per_min: int, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._max = max_per_min
        self._clock = clock
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = self._clock()
        window = [t for t in self._hits.get(key, []) if now - t < 60]
        if len(window) >= self._max:
            self._hits[key] = window
            return False
        window.append(now)
        self._hits[key] = window
        return True


def client_ip(request: Request) -> str:
    """Best-effort client IP for rate-limit keying. fly-client-ip is set by Fly's trusted
    proxy and is authoritative for the single-Fly deployment.
    """
    fly = request.headers.get("fly-client-ip")
    if fly:
        return fly
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


_limiter: RateLimiter | None = None


def _get_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = RateLimiter(get_config().WIDGET_TOKEN_RATELIMIT_PER_MIN)
    return _limiter


def enforce_widget_guard(request: Request) -> None:
    """FastAPI dependency: reject disallowed Origins (403) and rate-limited IPs (429).

    The Origin check runs first so a disallowed-origin flood is rejected without consuming
    the rate-limit budget.

    The trusted first-party voice worker (a valid X-Agent-Secret) is not a browser and has no
    real Origin, so it bypasses both checks. They exist to bound casual public abuse of the
    widget endpoints, not to gate our own backend-to-agent calls (availability, call close);
    without this the agent's own requests 403. A forged Origin is weaker than this secret, so
    honoring the secret does not loosen the guard for browsers.
    """
    if has_valid_agent_secret(request.headers.get("x-agent-secret")):
        return None
    cfg = get_config()
    allowed = cfg.WIDGET_ALLOWED_ORIGINS
    origin = request.headers.get("origin")
    if allowed and origin not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="origin not allowed")
    if not _get_limiter().allow(client_ip(request)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="rate limited")
    return None
