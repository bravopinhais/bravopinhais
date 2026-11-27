from __future__ import annotations

import pytest

from app.core.audit import AuditEvent
from app.core.postgres_module_settings import PostgresModuleSettingsRepository


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.closed = False

    def execute(self, sql, params=()):
        self.connection.calls.append((" ".join(sql.split()), params))

    def fetchall(self):
        return self.connection.rows

    def close(self):
        self.closed = True
        self.connection.cursor_closes += 1


class Connection:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.calls = []
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0
        self.cursor_closes = 0

    def cursor(self):
        return Cursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closes += 1


class Audit:
    def __init__(self, fail=False):
        self.events = []
        self.connections = []
        self.fail = fail

    def append_in_transaction(self, connection, event):
        self.connections.append(connection)
        if self.fail:
            raise RuntimeError("audit insert failed")
        self.events.append(event)


def event(key):
    return AuditEvent(
        actor_subject="google-subject-admin",
        action="configuracoes:alterar_modulo",
        entity_type="modulo",
        entity_id=key,
        outcome="success",
        request_id="req_config_test",
    )


def test_list_states_reads_only_persisted_module_settings():
    connection = Connection(rows=[("estoque", False), ("financeiro", True)])
    repository = PostgresModuleSettingsRepository(lambda: connection)

    result = repository.list_states()

    assert result == {"estoque": False, "financeiro": True}
    assert "select module_key, enabled from bravo_shadow.module_settings" in connection.calls[0][0].lower()
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closes == 1
    assert connection.cursor_closes == 1


def test_single_module_update_and_audit_share_one_transaction():
    connection = Connection()
    repository = PostgresModuleSettingsRepository(lambda: connection)
    audit = Audit()
    change_event = event("estoque")

    repository.set_state_audited(
        "estoque", False, event=change_event, audit_sink=audit
    )

    sql = [item[0].lower() for item in connection.calls]
    assert any("lock table bravo_shadow.module_settings" in item for item in sql)
    assert any("insert into bravo_shadow.module_settings" in item for item in sql)
    assert audit.events == [change_event]
    assert audit.connections == [connection]
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closes == 1


def test_audit_failure_rolls_back_module_state_change():
    connection = Connection()
    repository = PostgresModuleSettingsRepository(lambda: connection)
    audit = Audit(fail=True)

    with pytest.raises(RuntimeError, match="audit insert failed"):
        repository.set_state_audited(
            "estoque", False, event=event("estoque"), audit_sink=audit
        )

    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closes == 1


def test_bulk_update_requires_one_audit_event_per_module():
    connection = Connection()
    repository = PostgresModuleSettingsRepository(lambda: connection)
    audit = Audit()

    with pytest.raises(ValueError, match="exatamente um evento"):
        repository.set_states_audited(
            {"estoque": False, "financeiro": False},
            events=[event("estoque")],
            audit_sink=audit,
        )

    assert connection.calls == []
    assert connection.commits == 0


def test_bulk_update_writes_each_module_and_audit_event_atomically():
    connection = Connection()
    repository = PostgresModuleSettingsRepository(lambda: connection)
    audit = Audit()
    changes = {"estoque": False, "financeiro": False}
    events = [event("estoque"), event("financeiro")]

    repository.set_states_audited(changes, events=events, audit_sink=audit)

    writes = [sql for sql, _ in connection.calls if "insert into bravo_shadow.module_settings" in sql.lower()]
    assert len(writes) == 2
    assert audit.events == events
    assert audit.connections == [connection, connection]
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closes == 1
