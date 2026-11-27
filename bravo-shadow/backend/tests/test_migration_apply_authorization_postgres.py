"""Synthetic tests for locked persisted-approval reads; no database is used."""
from datetime import datetime, timezone

from app.core.migration_apply_authorization_postgres import load_locked_apply_authorization

H = "a" * 64
P = "b" * 64


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.row = None

    def execute(self, sql, params):
        self.connection.calls.append((" ".join(sql.split()), params))
        if "FROM bravo_shadow.migration_batches" in sql:
            self.row = self.connection.batch
        elif "FROM bravo_shadow.migration_executions" in sql:
            self.row = self.connection.execution
        elif "FROM bravo_shadow.migration_apply_approvals" in sql:
            self.row = self.connection.approval
        else:
            raise AssertionError("unexpected SQL")

    def fetchone(self):
        return self.row

    def close(self):
        self.connection.closed_cursors += 1


class Connection:
    def __init__(self):
        self.calls = []
        self.closed_cursors = 0
        self.batch = ("batch-1", H, "local_disposable", "approved")
        self.execution = (
            "exec-1", "batch-1", H, P, "local_disposable",
            "google-sub-requester", "approved",
        )
        self.approval = (
            "approval-1", "exec-1", "batch-1", H, P, "approved",
            "google-sub-reviewer", "Reviewed exact plan",
            datetime(2026, 11, 27, 20, 0, tzinfo=timezone.utc),
        )

    def cursor(self):
        return Cursor(self)


def load(connection):
    return load_locked_apply_authorization(
        connection, batch_id="batch-1", execution_id="exec-1",
        manifest_sha256=H, plan_sha256=P,
    )


def test_valid_persisted_approval_locks_in_fixed_order():
    connection = Connection()
    result = load(connection)
    assert result.authorized is True
    assert result.issues == ()
    assert len(connection.calls) == 3
    assert all("FOR UPDATE" in call[0] for call in connection.calls)
    assert "migration_batches" in connection.calls[0][0]
    assert "migration_executions" in connection.calls[1][0]
    assert "migration_apply_approvals" in connection.calls[2][0]
    assert connection.closed_cursors == 3


def test_batch_environment_or_status_blocks_before_execution_read():
    connection = Connection()
    connection.batch = ("batch-1", H, "ci_ephemeral", "approved")
    result = load(connection)
    assert result.authorized is False
    assert result.issues == ("batch_environment_not_allowed",)
    assert len(connection.calls) == 1


def test_missing_approval_fails_closed():
    connection = Connection()
    connection.approval = None
    result = load(connection)
    assert result.authorized is False
    assert result.issues == ("apply_approval_not_found",)


def test_changed_plan_is_rejected_by_persisted_approval():
    connection = Connection()
    result = load_locked_apply_authorization(
        connection, batch_id="batch-1", execution_id="exec-1",
        manifest_sha256=H, plan_sha256="c" * 64,
    )
    assert result.authorized is False
    assert "expected_plan_mismatch" in result.issues


def test_same_person_cannot_request_and_approve():
    connection = Connection()
    connection.approval = (
        "approval-1", "exec-1", "batch-1", H, P, "approved",
        "google-sub-requester", "Reviewed exact plan",
        datetime(2026, 11, 27, 20, 0, tzinfo=timezone.utc),
    )
    result = load(connection)
    assert result.authorized is False
    assert "requester_and_reviewer_must_differ" in result.issues


def test_no_connection_is_opened_or_required_by_importing_module():
    result = load_locked_apply_authorization(
        None, batch_id="batch-1", execution_id="exec-1",
        manifest_sha256=H, plan_sha256=P,
    )
    assert result.authorized is False
    assert result.issues == ("transaction_connection_required",)
