"""Unit tests for backend AI-cost telemetry (VoiceGateway).

Exercises both capture paths (the explicit onboarding recorder and the litellm-event mapper)
and the tenant attribution machinery, against a recording sink so no network is touched.
Records are plain dicts (the collector's /v1/ingest wire shape), so assertions use dict keys.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.telemetry import voicegateway as vg


class _RecordingSink:
    """A sink stand-in that keeps the record dicts it is handed."""

    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    async def log_request(self, record: dict[str, Any]) -> None:
        self.rows.append(record)

    async def aclose(self) -> None:
        pass


class _Usage:
    def __init__(self, prompt: int, completion: int) -> None:
        self.prompt_tokens = prompt
        self.completion_tokens = completion


class _Resp:
    def __init__(self, prompt: int, completion: int) -> None:
        self.usage = _Usage(prompt, completion)


@pytest.fixture
def sink():
    """Configure telemetry with a recording sink; reset module state after the test."""
    recording = _RecordingSink()
    vg.configure(recording)
    try:
        yield recording
    finally:
        vg._sink = None
        vg._installed = False


async def test_record_llm_usage_builds_priced_record(sink):
    await vg.record_llm_usage(
        model="gpt-4.1-mini",
        prompt_tokens=1000,
        completion_tokens=500,
        operation="onboard.extract_listings",
        tenant_id="realtor_X",
    )
    assert len(sink.rows) == 1
    row = sink.rows[0]
    assert row["project"] == "realty-recall"
    assert row["model_id"] == "openai/gpt-4.1-mini"
    assert row["provider"] == "openai"
    assert row["modality"] == "llm"
    assert row["input_units"] == 1000
    assert row["output_units"] == 500
    assert row["agent_id"] == "realtyrecall-backend"
    assert row["cost_usd"] > 0  # priced via voice-prices
    assert row["pricing_source"].startswith("voice-prices@")
    assert row["metadata"] == {
        "source": "backend",
        "kind": "completion",
        "operation": "onboard.extract_listings",
        "tenant_id": "realtor_X",
    }


async def test_record_llm_usage_reads_tenant_from_context(sink):
    with vg.attribute("realtor_ctx", "onboard.ingest"):
        await vg.record_llm_usage(
            model="gpt-4.1-mini",
            prompt_tokens=100,
            completion_tokens=10,
            operation="onboard.synthesize_profile",
        )
    assert sink.rows[0]["metadata"]["tenant_id"] == "realtor_ctx"


async def test_track_decorator_attributes_tenant(sink):
    @vg.track("cognee.recall")
    async def fake_op(tenant_id: str, query: str) -> str:
        # A memory op whose (simulated) AI call records under the ambient tenant.
        await vg.record_llm_usage(
            model="gpt-4o-mini", prompt_tokens=50, completion_tokens=5, operation="x"
        )
        return query

    await fake_op("realtor_dec", "find me a condo")
    assert sink.rows[0]["metadata"]["tenant_id"] == "realtor_dec"


async def test_litellm_completion_event_records(sink):
    kwargs = {"model": "gpt-4o-mini", "call_type": "acompletion"}
    with vg.attribute("realtor_L", "cognee.recall"):
        await vg._emit_from_litellm(kwargs, _Resp(prompt=800, completion=200))
    row = sink.rows[0]
    assert row["model_id"] == "openai/gpt-4o-mini"
    assert row["input_units"] == 800
    assert row["output_units"] == 200
    assert row["metadata"] == {
        "source": "backend",
        "kind": "completion",
        "operation": "cognee.recall",
        "tenant_id": "realtor_L",
    }


async def test_litellm_embedding_event_records_zero_output(sink):
    kwargs = {"model": "text-embedding-3-small", "call_type": "aembedding"}
    with vg.attribute("realtor_E", "cognee.add_listings"):
        await vg._emit_from_litellm(kwargs, _Resp(prompt=1000, completion=0))
    row = sink.rows[0]
    assert row["metadata"]["kind"] == "embedding"
    assert row["input_units"] == 1000
    assert row["output_units"] == 0


async def test_zero_usage_is_skipped(sink):
    await vg._emit_from_litellm(
        {"model": "gpt-4o-mini", "call_type": "acompletion"}, _Resp(0, 0)
    )
    assert sink.rows == []


async def test_prefixed_model_is_left_intact(sink):
    await vg.record_llm_usage(
        model="openai/gpt-4o-mini",
        prompt_tokens=10,
        completion_tokens=1,
        operation="x",
        tenant_id="t",
    )
    assert sink.rows[0]["model_id"] == "openai/gpt-4o-mini"
    assert sink.rows[0]["provider"] == "openai"


async def test_unknown_model_records_unpriced(sink):
    await vg.record_llm_usage(
        model="totally-made-up-model",
        prompt_tokens=100,
        completion_tokens=10,
        operation="x",
        tenant_id="t",
    )
    row = sink.rows[0]
    assert row["cost_usd"] == 0.0
    assert row["pricing_source"] == ""
    assert row["input_units"] == 100  # units still recorded


async def test_disabled_is_noop():
    # No configure() -> no sink -> a silent no-op that never raises.
    assert vg.enabled() is False
    await vg.record_llm_usage(
        model="gpt-4o-mini", prompt_tokens=10, completion_tokens=1, operation="x"
    )
