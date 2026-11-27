"""Synthetic transaction-boundary tests; no PostgreSQL connection is used."""
import pytest

from app.core.migration_transaction import (
    CommitOutcomeUnknown,
    MigrationApplyAuthorization,
    MigrationApplyBlocked,
    MigrationApplyCommand,
    apply_one_record,
)

MANIFEST = "a" * 64
PLAN = "b" * 64
RECORD = "c" * 64


class FakeConnection:
    autocommit = False

    def __init__(self, fail_commit=False):
        self.events = []
        self.fail_commit = fail_commit

    def commit(self):
        self.events.append("commit")
        if self.fail_commit:
            raise OSError("synthetic connection loss")

    def rollback(self):
        self.events.append("rollback")

    def close(self):
        self.events.append("close")


class FakeStore:
    def __init__(self, fail_at=None, existing=None, target_exists=False):
        self.fail_at = fail_at
        self.existing = existing
        self.target_exists = target_exists
        self.events = []

    def _step(self, name, connection):
        assert connection is self.connection
        self.events.append(name)
        if self.fail_at == name:
            raise RuntimeError("synthetic failure")

    def bind(self, connection):
        self.connection = connection

    def lock_batch(self, connection, batch_id, execution_id):
        self._step("lock_batch", connection)

    def lock_source_identity(self, connection, source_system, source_collection, legacy_id):
        self._step("lock_identity", connection)

    def find_source_link(self, connection, source_system, source_collection, legacy_id):
        self._step("find_link", connection)
        return self.existing

    def target_id_exists(self, connection, target_collection, destination_id):
        self._step("check_target", connection)
        return self.target_exists

    def insert_target(self, connection, target_collection, destination_id, payload):
        self._step("insert_target", connection)

    def insert_source_link(self, connection, command):
        self._step("insert_link", connection)

    def insert_success_event(self, connection, command, destination_id):
        self._step("insert_success_event", connection)


def setup(store=None, connection=None):
    conn = connection or FakeConnection()
    repo = store or FakeStore()
    repo.bind(conn)
    command = MigrationApplyCommand(
        "batch-1", "execution-1", "legacy", "estoque", "0007", RECORD,
        "sha256-json-v1", "estoque", {"item": "caneta"}, "0007", MANIFEST, PLAN,
    )
    permit = MigrationApplyAuthorization(MANIFEST, PLAN, "shadow_local", "migration_apply", True)
    return conn, repo, command, permit


def test_success_uses_one_connection_and_commits_after_all_three_writes():
    conn, store, command, permit = setup()
    result = apply_one_record(lambda: conn, store, command, permit)
    assert result.classification == "applied"
    assert store.events[-3:] == ["insert_target", "insert_link", "insert_success_event"]
    assert conn.events == ["commit", "close"]


@pytest.mark.parametrize("failure", ["insert_target", "insert_link", "insert_success_event"])
def test_any_write_failure_rolls_back_entire_unit(failure):
    conn, store, command, permit = setup(FakeStore(fail_at=failure))
    with pytest.raises(RuntimeError):
        apply_one_record(lambda: conn, store, command, permit)
    assert conn.events == ["rollback", "close"]


def test_identical_retry_is_idempotent_without_business_writes():
    conn, store, command, permit = setup(FakeStore(existing=(RECORD, "0007")))
    result = apply_one_record(lambda: conn, store, command, permit)
    assert result.classification == "already_applied"
    assert store.events == ["lock_batch", "lock_identity", "find_link"]
    assert conn.events == ["commit", "close"]


def test_changed_source_hash_is_blocked_and_rolled_back():
    conn, store, command, permit = setup(FakeStore(existing=("d" * 64, "0007")))
    with pytest.raises(MigrationApplyBlocked, match="conflict_changed_source"):
        apply_one_record(lambda: conn, store, command, permit)
    assert conn.events == ["rollback", "close"]


def test_unmapped_destination_collision_is_blocked():
    conn, store, command, permit = setup(FakeStore(target_exists=True))
    with pytest.raises(MigrationApplyBlocked, match="destination_id_collision"):
        apply_one_record(lambda: conn, store, command, permit)
    assert conn.events == ["rollback", "close"]


def test_uncertain_commit_is_not_reported_as_success():
    conn, store, command, permit = setup(connection=FakeConnection(fail_commit=True))
    with pytest.raises(CommitOutcomeUnknown):
        apply_one_record(lambda: conn, store, command, permit)
    assert conn.events == ["commit", "rollback", "close"]


def test_manifest_plan_or_environment_mismatch_blocks_before_connecting():
    _, store, command, permit = setup()
    bad = MigrationApplyAuthorization(MANIFEST, PLAN, "production", "migration_apply", True)
    called = []
    with pytest.raises(MigrationApplyBlocked):
        apply_one_record(lambda: called.append(True), store, command, bad)
    assert called == []


def test_autocommit_connection_is_rejected():
    conn, store, command, permit = setup()
    conn.autocommit = True
    with pytest.raises(MigrationApplyBlocked):
        apply_one_record(lambda: conn, store, command, permit)
    assert conn.events == ["rollback", "close"]


class CloseFailConnection(FakeConnection):
    def close(self):
        self.events.append("close")
        raise OSError("synthetic close failure")


def test_commit_success_followed_by_close_failure_is_not_misreported_as_rollback():
    conn, store, command, permit = setup(connection=CloseFailConnection())
    from app.core.postgres import CommitSucceededCleanupError
    with pytest.raises(CommitSucceededCleanupError):
        apply_one_record(lambda: conn, store, command, permit)
    assert conn.events == ["commit", "close"]
    assert store.events[-3:] == ["insert_target", "insert_link", "insert_success_event"]


def test_connection_factory_must_return_complete_dbapi_unit_of_work():
    _, store, command, permit = setup()
    with pytest.raises(TypeError, match="commit, rollback e close"):
        apply_one_record(lambda: object(), store, command, permit)
