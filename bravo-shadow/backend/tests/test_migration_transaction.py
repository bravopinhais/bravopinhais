import pytest

from app.core.migration_transaction import (
    MigrationWriteOperations,
    execute_migration_write_unit,
)
from app.core.postgres import PostgresUnitOfWork


class FakeConnection:
    def __init__(self):
        self.calls = []
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closes += 1


def make_operations(expected_connection, calls, *, fail_at=None):
    def record(step, connection):
        assert connection is expected_connection
        calls.append(step)
        if fail_at == step:
            raise RuntimeError(f"failure_at_{step}")

    def reserve(connection):
        record("reserve", connection)

    def write_business(connection):
        record("business", connection)
        return {"table": "fornecedores", "id": "legacy-17"}

    def write_source_map(connection, destination):
        assert destination["id"] == "legacy-17"
        record("source_map", connection)

    def append_event(connection, destination):
        assert destination["table"] == "fornecedores"
        record("success_event", connection)

    def append_audit(connection, destination):
        assert destination["id"] == "legacy-17"
        record("audit_event", connection)

    def append_failure(error):
        calls.append(("failure_event", type(error).__name__, expected_connection.rollbacks))

    return MigrationWriteOperations(
        reserve_batch=reserve,
        write_business=write_business,
        write_source_map=write_source_map,
        append_success_event=append_event,
        append_audit_event=append_audit,
        append_failure_event=append_failure,
    )


def test_write_unit_uses_one_connection_and_commits_all_steps():
    connection = FakeConnection()
    calls = []
    operations = make_operations(connection, calls)

    result = execute_migration_write_unit(
        lambda: PostgresUnitOfWork(lambda: connection),
        operations,
    )

    assert result == {"table": "fornecedores", "id": "legacy-17"}
    assert calls == ["reserve", "business", "source_map", "success_event", "audit_event"]
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closes == 1


@pytest.mark.parametrize(
    ("failed_step", "expected_calls"),
    [
        ("reserve", ["reserve"]),
        ("business", ["reserve", "business"]),
        ("source_map", ["reserve", "business", "source_map"]),
        (
            "success_event",
            ["reserve", "business", "source_map", "success_event"],
        ),
        (
            "audit_event",
            ["reserve", "business", "source_map", "success_event", "audit_event"],
        ),
    ],
)
def test_failure_at_any_step_rolls_back_entire_unit(failed_step, expected_calls):
    connection = FakeConnection()
    calls = []
    operations = make_operations(connection, calls, fail_at=failed_step)

    with pytest.raises(RuntimeError, match=f"failure_at_{failed_step}"):
        execute_migration_write_unit(
            lambda: PostgresUnitOfWork(lambda: connection),
            operations,
        )

    assert calls[:len(expected_calls)] == expected_calls
    assert calls[-1] == ("failure_event", "RuntimeError", 1)
    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closes == 1


def test_unit_does_not_emit_success_event_when_business_insert_fails():
    connection = FakeConnection()
    calls = []
    operations = make_operations(connection, calls, fail_at="business")

    with pytest.raises(RuntimeError):
        execute_migration_write_unit(
            lambda: PostgresUnitOfWork(lambda: connection),
            operations,
        )

    assert "source_map" not in calls
    assert "success_event" not in calls
    assert "audit_event" not in calls
    assert calls[-1] == ("failure_event", "RuntimeError", 1)
    assert connection.rollbacks == 1


def test_failure_audit_error_does_not_hide_original_migration_error():
    connection = FakeConnection()
    calls = []
    operations = make_operations(connection, calls, fail_at="business")

    def broken_failure_audit(error):
        calls.append(("failure_audit_error", type(error).__name__, connection.rollbacks))
        raise RuntimeError("failure_audit_unavailable")

    operations = MigrationWriteOperations(
        reserve_batch=operations.reserve_batch,
        write_business=operations.write_business,
        write_source_map=operations.write_source_map,
        append_success_event=operations.append_success_event,
        append_audit_event=operations.append_audit_event,
        append_failure_event=broken_failure_audit,
    )

    with pytest.raises(RuntimeError, match="failure_at_business") as caught:
        execute_migration_write_unit(
            lambda: PostgresUnitOfWork(lambda: connection), operations
        )

    assert connection.rollbacks == 1
    assert calls[-1] == ("failure_audit_error", "RuntimeError", 1)
    assert any("auditoria de falha" in note for note in getattr(caught.value, "__notes__", []))
