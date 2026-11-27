from datetime import datetime, timezone

import pytest

from app.core.audit import AuditEvent
from app.core.postgres_audit import PostgresAuditSink


class FakeCursor:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.calls = []
        self.closed = False

    def execute(self, sql, params):
        self.calls.append((sql, params))
        if self.fail:
            raise RuntimeError("insert failed")

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, *, fail=False):
        self.cursor_instance = FakeCursor(fail=fail)
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closes += 1


def make_event():
    return AuditEvent(
        actor_subject="google-subject-123",
        action="financeiro:create",
        entity_type="financeiro",
        entity_id="fin_123",
        outcome="success",
        request_id="req_123",
        occurred_at=datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc),
    )


def test_postgres_sink_inserts_only_audit_fields_and_commits():
    connection = FakeConnection()
    sink = PostgresAuditSink(lambda: connection)

    event = make_event()
    sink.append(event)

    sql, params = connection.cursor_instance.calls[0]
    assert "INSERT INTO bravo_shadow.audit_events" in sql
    assert params == (
        event.event_id,
        event.occurred_at,
        "google-subject-123",
        "financeiro:create",
        "financeiro",
        "fin_123",
        "success",
        "req_123",
    )
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closes == 1
    assert connection.cursor_instance.closed is True


def test_postgres_sink_rolls_back_when_insert_fails():
    connection = FakeConnection(fail=True)
    sink = PostgresAuditSink(lambda: connection)

    with pytest.raises(RuntimeError, match="insert failed"):
        sink.append(make_event())

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closes == 1
    assert connection.cursor_instance.closed is True


def test_postgres_sink_rejects_non_event_before_opening_connection():
    opened = False

    def factory():
        nonlocal opened
        opened = True
        return FakeConnection()

    sink = PostgresAuditSink(factory)

    with pytest.raises(TypeError, match="AuditEvent"):
        sink.append({"action": "financeiro:create"})

    assert opened is False


def test_append_in_transaction_does_not_commit_or_close_connection():
    connection = FakeConnection()
    sink = PostgresAuditSink(lambda: pytest.fail("factory não deve ser usada"))
    event = make_event()

    sink.append_in_transaction(connection, event)

    sql, params = connection.cursor_instance.calls[0]
    assert "INSERT INTO bravo_shadow.audit_events" in sql
    assert params[0] == event.event_id
    assert connection.commits == 0
    assert connection.rollbacks == 0
    assert connection.closes == 0
    assert connection.cursor_instance.closed is True


def test_append_in_transaction_propagates_error_without_owning_transaction():
    connection = FakeConnection(fail=True)
    sink = PostgresAuditSink(lambda: pytest.fail("factory não deve ser usada"))

    with pytest.raises(RuntimeError, match="insert failed"):
        sink.append_in_transaction(connection, make_event())

    assert connection.commits == 0
    assert connection.rollbacks == 0
    assert connection.closes == 0
    assert connection.cursor_instance.closed is True

@pytest.mark.parametrize("connection", [None, object(), {"cursor": "not-callable"}])
def test_append_in_transaction_rejects_invalid_connection(connection):
    sink = PostgresAuditSink(lambda: pytest.fail("factory não deve ser usada"))

    with pytest.raises(TypeError, match="conexão DB-API"):
        sink.append_in_transaction(connection, make_event())

