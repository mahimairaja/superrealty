"""Backend AI-cost telemetry: push the hidden Cognee + onboarding spend to VoiceGateway.

The voice agent's per-call STT/LLM/TTS cost is captured in the agent process (see the
agent's voicegateway.attach). But a realtor also costs money the moment they onboard and
every time memory is read or written: the onboarding extraction LLM calls, and Cognee's
own LLM completions + embeddings behind add/cognify/search/improve. That spend is invisible
to the call-level view. This module surfaces it, attributed to the same realtor (tenant) and
the same ``realty-recall`` project, so the true cost-to-serve per realtor is one number.

Two capture paths, one recorder:

* Cognee routes every LLM completion and embedding through **litellm**, so a single
  litellm success callback captures them all. Attribution rides a ``ContextVar`` set around
  each memory op (see ``track``); litellm invokes the async callback in the originating
  task's context, so the right tenant is in scope when it fires.
* The onboarding extractor (``llm_service``) calls the OpenAI SDK directly, which litellm
  never sees, so it records usage explicitly via ``record_llm_usage`` (reading the same
  ContextVar for the tenant).

Deliberately decoupled from the VoiceGateway engine package: it prices with ``voice-prices``
(the same catalog the agent uses, so backend and voice cost are comparable) and POSTs the
records straight to the collector's ``/v1/ingest``. Importing the engine's ORM here would
collide with the backend's own SQLModel ``tenants`` table, so we build plain record dicts and
the collector fills the rest. Everything is best-effort: a missing collector config, a pricing
miss, or a sink error is swallowed and logged at debug. It must never slow or break a request.
"""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import functools
import inspect
import logging
import os
import time
import uuid
from collections.abc import Awaitable, Callable, Iterator
from typing import Any, TypeVar

logger = logging.getLogger("telemetry")

# All backend rows share the agent's project so voice + backend cost sum per realtor, and
# carry an agent_id that marks them as the backend tier (distinct from the voice worker).
_PROJECT = "realty-recall"
_AGENT_ID = "realtyrecall-backend"

_tenant: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "vg_tenant", default=None
)
_operation: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "vg_operation", default=None
)

# Built lazily from env on install(); left None (a clean no-op) when unconfigured, so the
# backend runs unchanged without a collector.
_sink: Any | None = None
_installed = False

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def enabled() -> bool:
    """True when a collector sink is configured and telemetry will emit."""
    return _sink is not None


def configure(sink: Any) -> None:
    """Set the sink that records are handed to (a ``_Collector`` in prod, a fake in tests)."""
    global _sink
    _sink = sink


def install() -> None:
    """Build the collector from env and register the litellm capture callback. Idempotent.

    Reads ``VOICEGW_COLLECTOR_URL`` + ``VOICEGW_API_KEY`` (the same vars the agent uses). With
    no collector URL this is a no-op and ``enabled()`` stays False. Safe to call at startup.
    """
    global _installed
    if _installed:
        return
    _installed = True
    try:
        if _sink is None:
            url = os.environ.get("VOICEGW_COLLECTOR_URL")
            if url:
                configure(_Collector(url, os.environ.get("VOICEGW_API_KEY")))
        if _sink is not None:
            _install_litellm_callback()
            logger.info("VoiceGateway backend telemetry enabled (project=%s)", _PROJECT)
    except Exception:  # noqa: BLE001 - telemetry never blocks startup
        logger.warning("VoiceGateway telemetry install failed; continuing", exc_info=True)


async def aclose() -> None:
    """Flush and close the sink on shutdown so a buffered final batch is not lost."""
    if _sink is None:
        return
    close = getattr(_sink, "aclose", None)
    if close is None:
        return
    try:
        await close()
    except Exception:  # noqa: BLE001 - best-effort drain
        logger.debug("telemetry: sink aclose failed", exc_info=True)


@contextlib.contextmanager
def attribute(tenant_id: str | None, operation: str) -> Iterator[None]:
    """Scope the current context to a tenant + operation for the duration of a block.

    The litellm callback and ``record_llm_usage`` read these, so any AI call made inside the
    block is attributed to ``tenant_id``. Nestable and reset-safe.
    """
    t1 = _tenant.set(tenant_id)
    t2 = _operation.set(operation)
    try:
        yield
    finally:
        _tenant.reset(t1)
        _operation.reset(t2)


def track(operation: str) -> Callable[[F], F]:
    """Decorate an async memory op so its Cognee AI calls attribute to its ``tenant_id`` arg.

    Reads ``tenant_id`` from the wrapped call's bound arguments (positional or keyword) and
    holds it in the ContextVar while the op runs, so the litellm callback sees it. A method
    with no ``tenant_id`` still runs; it just attributes to None.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            with attribute(_bound_tenant(func, args, kwargs), operation):
                return await func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def _bound_tenant(func: Callable[..., Any], args: tuple, kwargs: dict) -> str | None:
    try:
        bound = inspect.signature(func).bind_partial(*args, **kwargs)
        value = bound.arguments.get("tenant_id")
        return value if isinstance(value, str) else None
    except Exception:  # noqa: BLE001 - never let attribution break the call
        return None


async def record_llm_usage(
    *,
    model: str,
    prompt_tokens: float,
    completion_tokens: float = 0.0,
    operation: str,
    provider: str | None = None,
    kind: str = "completion",
    tenant_id: str | None = None,
) -> None:
    """Record one text-model call's usage (the OpenAI-SDK path litellm never sees).

    ``tenant_id`` defaults to the current ``attribute`` scope. Prices via voice-prices, the
    same catalog the agent rows use, so backend and voice cost are directly comparable.
    """
    await _emit(
        model=model,
        provider=provider,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        kind=kind,
        operation=operation,
        tenant_id=tenant_id if tenant_id is not None else _tenant.get(),
    )


def _install_litellm_callback() -> None:
    import litellm
    from litellm.integrations.custom_logger import CustomLogger

    class _VGUsageLogger(CustomLogger):
        async def async_log_success_event(
            self, kwargs: dict, response_obj: Any, start_time: Any, end_time: Any
        ) -> None:
            try:
                await _emit_from_litellm(kwargs, response_obj)
            except Exception:  # noqa: BLE001 - a telemetry miss never fails a Cognee call
                logger.debug("telemetry: litellm capture failed", exc_info=True)

    # Idempotent: only add our logger once, even if install() somehow runs twice.
    if not any(isinstance(cb, _VGUsageLogger) for cb in litellm.callbacks):
        litellm.callbacks.append(_VGUsageLogger())


async def _emit_from_litellm(kwargs: dict, response_obj: Any) -> None:
    """Map a litellm success event (Cognee's completions + embeddings) to a usage record."""
    usage = getattr(response_obj, "usage", None)
    prompt = float(getattr(usage, "prompt_tokens", 0) or 0)
    completion = float(getattr(usage, "completion_tokens", 0) or 0)
    if prompt <= 0 and completion <= 0:
        return  # nothing metered (e.g. a cache hit) -> skip
    call_type = str(kwargs.get("call_type") or "").lower()
    provider = kwargs.get("custom_llm_provider") or (
        kwargs.get("litellm_params") or {}
    ).get("custom_llm_provider")
    await _emit(
        model=str(kwargs.get("model") or ""),
        provider=provider,
        prompt_tokens=prompt,
        completion_tokens=completion,
        kind="embedding" if "embed" in call_type else "completion",
        operation=_operation.get() or "cognee",
        tenant_id=_tenant.get(),
    )


async def _emit(
    *,
    model: str,
    provider: str | None,
    prompt_tokens: float,
    completion_tokens: float,
    kind: str,
    operation: str,
    tenant_id: str | None,
) -> None:
    if _sink is None or not model:
        return
    try:
        norm_provider, model_id = _normalize_model(model, provider)
        # Embeddings have no output price; passing 0 keeps the priced row honest.
        output_units = completion_tokens if kind != "embedding" else 0.0
        cost_usd, pricing_source = _price(model_id, prompt_tokens, output_units, kind)
        record = {
            "id": uuid.uuid4().hex,
            "timestamp": time.time(),
            "modality": "llm",
            "model_id": model_id,
            "provider": norm_provider,
            "project": _PROJECT,
            "input_units": prompt_tokens,
            "output_units": output_units,
            "cost_usd": cost_usd,
            "pricing_source": pricing_source,
            "status": "success",
            "agent_id": _AGENT_ID,
            "metadata": {
                "source": "backend",
                "kind": kind,
                "operation": operation,
                **({"tenant_id": tenant_id} if tenant_id else {}),
            },
        }
        await _sink.log_request(record)
    except Exception:  # noqa: BLE001 - telemetry is never load-bearing
        logger.debug("telemetry: emit failed (model=%s)", model, exc_info=True)


def _normalize_model(model: str, provider: str | None) -> tuple[str, str]:
    """Return ``(provider, provider/model)`` for pricing. litellm may hand us either a bare
    model (``gpt-4.1-mini``) or an already-prefixed one (``openai/gpt-4o-mini``).
    """
    if "/" in model:
        head, _, _tail = model.partition("/")
        return (provider or head), model
    resolved = provider or "openai"
    return resolved, f"{resolved}/{model}"


def _price(
    model_id: str, input_units: float, output_units: float, kind: str
) -> tuple[float, str]:
    """Price a text-model call via voice-prices; (0.0, "") when the model is unknown.

    Mirrors the engine's LLM pricing so backend rows match the agent's. Embeddings pass no
    output tokens (there is no output price). Best-effort: any pricing error yields an unpriced
    row (units still recorded) rather than dropping the record.
    """
    provider, _, ref = model_id.partition("/")
    try:
        import voice_prices
        from voice_prices import Usage, calc_price

        usage = Usage(
            input_tokens=int(input_units),
            output_tokens=int(output_units) if kind != "embedding" else None,
        )
        price = calc_price(usage, model_ref=ref, provider_id=provider or None)
    except LookupError:
        return 0.0, ""
    except Exception:  # noqa: BLE001 - unpriced is fine; never raise into a request
        logger.debug("telemetry: pricing failed (%s)", model_id, exc_info=True)
        return 0.0, ""
    if price is None:
        return 0.0, ""
    return float(price.total_price), f"voice-prices@{voice_prices.__version__}"


class _Collector:
    """A tiny best-effort client that batches usage records and POSTs them to /v1/ingest.

    Mirrors the engine's RemoteCollectorSink at a smaller scale: buffer in memory, flush on
    batch size or a periodic interval, drain on close. Telemetry is not billing-of-record, so
    a failed POST drops the batch rather than blocking or raising into a realtor's request.
    """

    def __init__(
        self,
        url: str,
        api_key: str | None,
        *,
        batch_size: int = 25,
        flush_interval: float = 3.0,
        timeout: float = 10.0,
    ) -> None:
        self._ingest_url = url.rstrip("/") + "/v1/ingest"
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._batch_size = max(1, batch_size)
        self._flush_interval = flush_interval
        self._timeout = timeout
        self._buffer: list[dict] = []
        self._client: Any = None
        self._flusher: asyncio.Task | None = None
        self._closed = False

    async def log_request(self, record: dict) -> None:
        if self._closed:
            return
        self._buffer.append(record)
        self._ensure_flusher()
        if len(self._buffer) >= self._batch_size:
            await self._flush()

    def _ensure_flusher(self) -> None:
        if self._flusher is not None or not self._flush_interval:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._flusher = loop.create_task(self._periodic())

    async def _periodic(self) -> None:
        try:
            while not self._closed:
                await asyncio.sleep(self._flush_interval)
                await self._flush()
        except asyncio.CancelledError:
            pass

    async def _flush(self) -> None:
        if not self._buffer:
            return
        batch, self._buffer = self._buffer, []
        try:
            import httpx

            if self._client is None:
                self._client = httpx.AsyncClient(timeout=self._timeout)
            await self._client.post(self._ingest_url, json=batch, headers=self._headers)
        except Exception:  # noqa: BLE001 - drop, never block the app
            logger.debug(
                "telemetry: flush dropped %d row(s)", len(batch), exc_info=True
            )

    async def aclose(self) -> None:
        self._closed = True
        if self._flusher is not None:
            self._flusher.cancel()
            with contextlib.suppress(Exception):
                await self._flusher
        await self._flush()
        if self._client is not None:
            with contextlib.suppress(Exception):
                await self._client.aclose()
