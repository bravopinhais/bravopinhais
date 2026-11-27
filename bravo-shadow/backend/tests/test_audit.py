from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from app.core.audit import AuditEvent, InMemoryAuditSink


def make_event(**overrides):
    values = {
        "actor_subject": "google-subject-123",
        "action": "financeiro:create",
        "entity_type": "financeiro",
        "entity_id": "fin_123",
        "outcome": "success",
    }
    values.update(overrides)
    return AuditEvent(**values)


def test_audit_event_uses_timezone_aware_timestamp():
    event = make_event()
    assert event.occurred_at.tzinfo is not None
    assert event.occurred_at.utcoffset() is not None


def test_audit_event_rejects_naive_timestamp():
    with pytest.raises(ValueError, match="fuso horário"):
        make_event(occurred_at=datetime(2026, 11, 26, 12, 0, 0))


def test_audit_event_rejects_blank_required_fields():
    with pytest.raises(ValueError, match="actor_subject"):
        make_event(actor_subject="   ")


def test_audit_event_rejects_unknown_outcome():
    with pytest.raises(ValueError, match="outcome"):
        make_event(outcome="pending")


def test_sink_appends_events_and_returns_immutable_snapshot():
    sink = InMemoryAuditSink()
    first = make_event()
    sink.append(first)
    snapshot = sink.list_events()
    sink.append(make_event(action="financeiro:update"))
    assert snapshot == (first,)
    assert len(sink.list_events()) == 2
    assert isinstance(sink.list_events(), tuple)


def test_audit_event_is_immutable():
    event = make_event()
    with pytest.raises(FrozenInstanceError):
        event.action = "usuarios:update_profile"


def test_sink_rejects_non_audit_objects():
    sink = InMemoryAuditSink()
    with pytest.raises(TypeError, match="AuditEvent"):
        sink.append({"action": "financeiro:create"})

def test_audit_event_schema_contains_only_explicit_minimal_fields():
    from dataclasses import fields

    assert {item.name for item in fields(AuditEvent)} == {
        "actor_subject",
        "action",
        "entity_type",
        "entity_id",
        "outcome",
        "request_id",
        "event_id",
        "occurred_at",
    }


def test_audit_event_does_not_accept_unreviewed_payload_fields():
    with pytest.raises(TypeError):
        make_event(email="person@example.com")
    with pytest.raises(TypeError):
        make_event(metadata={"token": "must-not-be-stored"})


@pytest.mark.parametrize("outcome", ["success", "denied", "failure"])
def test_audit_event_accepts_each_supported_outcome(outcome):
    event = make_event(outcome=outcome)
    assert event.outcome == outcome


@pytest.mark.parametrize("event_id", ["", "   ", None, [], {}])
def test_audit_event_rejects_invalid_event_id(event_id):
    with pytest.raises(ValueError, match="event_id"):
        make_event(event_id=event_id)


@pytest.mark.parametrize("occurred_at", [None, "2026-11-26T12:00:00Z", 123, []])
def test_audit_event_rejects_non_datetime_timestamp(occurred_at):
    with pytest.raises(ValueError, match="data/hora válida"):
        make_event(occurred_at=occurred_at)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("actor_subject", None),
        ("actor_subject", 123),
        ("action", []),
        ("entity_type", {}),
        ("entity_id", 123),
        ("request_id", []),
        ("outcome", []),
        ("outcome", {}),
    ],
)
def test_audit_event_rejects_malformed_field_types(field, value):
    with pytest.raises(ValueError):
        make_event(**{field: value})
