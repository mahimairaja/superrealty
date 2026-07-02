"""Tests for room utilities."""

from types import SimpleNamespace

import pytest
from livekit import rtc

from src.utils.room import (
    Caller,
    identify,
    parse_room_metadata,
    parse_tenant_id,
    resolve_tenant_id,
    tenant_from_metadata,
)


def _participant(
    identity="u1",
    kind=rtc.ParticipantKind.PARTICIPANT_KIND_STANDARD,
    attributes=None,
):
    return SimpleNamespace(identity=identity, kind=kind, attributes=attributes or {})


def test_parse_valid_json():
    assert parse_room_metadata('{"source": "sandbox"}') == {"source": "sandbox"}


def test_parse_empty():
    assert parse_room_metadata(None) == {}
    assert parse_room_metadata("") == {}


def test_parse_invalid_json():
    assert parse_room_metadata("not json") == {}


def test_parse_non_dict_json():
    assert parse_room_metadata("[1,2,3]") == {}


def test_identify_web_participant():
    caller = identify(_participant(identity="web-user"))
    assert caller == Caller(kind="web", identity="web-user", phone=None)


def test_identify_sip_by_attribute():
    caller = identify(_participant(attributes={"sip.phoneNumber": "+14165550000"}))
    assert caller.kind == "sip"
    assert caller.phone == "+14165550000"


def test_identify_sip_by_kind():
    caller = identify(_participant(kind=rtc.ParticipantKind.PARTICIPANT_KIND_SIP))
    assert caller.kind == "sip"


def test_parse_tenant_id_round_trips_org_with_underscores():
    # The Clerk org id contains underscores; the random suffix does not, so the tenant is
    # everything before the LAST underscore. Must match the backend codec.
    assert parse_tenant_id("t_org_2abCDef_GhiJkl_9f8e7d6c5b4a") == "org_2abCDef_GhiJkl"
    assert parse_tenant_id("t_org_simple_abcdef123456") == "org_simple"


@pytest.mark.parametrize(
    "room",
    [None, "", "plain-room", "room-abc123", "t_", "t_onlytenant"],
)
def test_parse_tenant_id_rejects_non_tenant_rooms(room):
    assert parse_tenant_id(room) is None


def test_tenant_from_metadata_reads_tenant_id():
    # SIP dispatch passes the tenant as job metadata since the room name can't carry it.
    assert tenant_from_metadata('{"tenant_id": "org_abc"}') == "org_abc"


@pytest.mark.parametrize(
    "raw",
    [None, "", "not json", "{}", '{"tenant_id": ""}', '{"tenant_id": 5}', "[1,2]"],
)
def test_tenant_from_metadata_missing_or_bad(raw):
    assert tenant_from_metadata(raw) is None


def test_resolve_tenant_prefers_room_name():
    # The web/console path: the codec room name wins even if metadata is also present.
    assert (
        resolve_tenant_id(
            "t_org_web_9f8e7d6c5b4a",
            '{"tenant_id": "org_job"}',
            '{"tenant_id": "org_room"}',
        )
        == "org_web"
    )


def test_resolve_tenant_falls_back_to_job_metadata():
    # The SIP path: no tenant in the provider-named room, so the dispatch job metadata is used.
    assert (
        resolve_tenant_id("sip-inbound-abc", '{"tenant_id": "org_job"}', None)
        == "org_job"
    )


def test_resolve_tenant_falls_back_to_room_metadata():
    # The direct-dispatch path (e.g. Cekura LiveKit v2): the dispatcher names its own room and
    # passes the tenant as room metadata, which the config JSON lands in.
    assert (
        resolve_tenant_id("cekura-room-xyz", None, '{"tenant_id": "org_room"}')
        == "org_room"
    )


def test_resolve_tenant_none_when_no_carrier():
    assert resolve_tenant_id("plain-room", None, None) is None
    assert resolve_tenant_id(None, "not json", "{}") is None
