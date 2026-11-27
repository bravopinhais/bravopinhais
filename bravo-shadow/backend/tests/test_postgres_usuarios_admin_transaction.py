import pytest
from fastapi import HTTPException

from app.core.audit import AuditEvent
from app.core.postgres_usuarios import PostgresUsuariosRepository


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.rowcount = 1
        self.pending = None
        self.closed = False

    def execute(self, sql, params=()):
        self.connection.calls.append((sql, params))
        normalized = " ".join(sql.split()).lower()
        if normalized.startswith("select perfil, status"):
            self.pending = self.connection.target
        elif normalized.startswith("select count(*)"):
            self.pending = (self.connection.active_admins,)
        elif normalized.startswith("update "):
            self.connection.updated = True

    def fetchone(self):
        return self.pending

    def close(self):
        self.closed = True


class Connection:
    def __init__(self, *, target=("Admin", "Ativo"), active_admins=2):
        self.target = target
        self.active_admins = active_admins
        self.calls = []
        self.cursor_instance = Cursor(self)
        self.updated = False
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


class AuditSink:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.calls = []

    def append_in_transaction(self, connection, event):
        self.calls.append((connection, event))
        if self.fail:
            raise RuntimeError("audit insert failed")


def make_event():
    return AuditEvent(
        actor_subject="google-subject-admin",
        action="usuarios:update_administracao",
        entity_type="usuario",
        entity_id="usr_target",
    )


def make_repository(connection):
    return PostgresUsuariosRepository(lambda: connection)


def test_admin_state_change_updates_and_audits_in_same_transaction():
    connection = Connection(active_admins=2)
    sink = AuditSink()
    repository = make_repository(connection)

    repository.update_administrative_state(
        "usr_target", perfil="Operador", status="Ativo",
        event=make_event(), audit_sink=sink,
    )

    assert connection.updated is True
    assert sink.calls == [(connection, sink.calls[0][1])]
    assert sink.calls[0][1].entity_id == "usr_target"
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closes == 1
    assert any("LOCK TABLE bravo_shadow.usuarios IN SHARE ROW EXCLUSIVE MODE" in sql
               for sql, _ in connection.calls)


def test_last_active_admin_cannot_be_demoted_or_deactivated():
    connection = Connection(active_admins=1)
    sink = AuditSink()
    repository = make_repository(connection)

    with pytest.raises(HTTPException) as error:
        repository.update_administrative_state(
            "usr_target", perfil="Operador", status="Ativo",
            event=make_event(), audit_sink=sink,
        )

    assert error.value.status_code == 409
    assert connection.updated is False
    assert sink.calls == []
    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closes == 1


def test_audit_failure_rolls_back_administrative_change():
    connection = Connection(active_admins=2)
    sink = AuditSink(fail=True)
    repository = make_repository(connection)

    with pytest.raises(RuntimeError, match="audit insert failed"):
        repository.update_administrative_state(
            "usr_target", perfil="Operador", status="Ativo",
            event=make_event(), audit_sink=sink,
        )

    assert connection.updated is True
    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closes == 1


def test_missing_user_does_not_update_or_audit():
    connection = Connection(target=None)
    sink = AuditSink()
    repository = make_repository(connection)

    with pytest.raises(HTTPException) as error:
        repository.update_administrative_state(
            "usr_missing", perfil="Operador", status="Ativo",
            event=AuditEvent(
                actor_subject="google-subject-admin",
                action="usuarios:update_administracao",
                entity_type="usuario",
                entity_id="usr_missing",
            ),
            audit_sink=sink,
        )

    assert error.value.status_code == 404
    assert connection.updated is False
    assert sink.calls == []
    assert connection.rollbacks == 1



def make_deactivation_event():
    return AuditEvent(
        actor_subject="google-subject-admin",
        action="usuarios:desativar",
        entity_type="usuario",
        entity_id="usr_target",
    )


def test_deactivation_preserves_user_and_audits_in_same_transaction():
    connection = Connection(target=("Operador", "Ativo"))
    sink = AuditSink()
    make_repository(connection).deactivate_user(
        "usr_target", event=make_deactivation_event(), audit_sink=sink
    )

    assert connection.updated is True
    assert sink.calls[0][0] is connection
    assert sink.calls[0][1].action == "usuarios:desativar"
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closes == 1


def test_last_active_admin_cannot_be_deactivated():
    connection = Connection(target=("Admin", "Ativo"), active_admins=1)
    sink = AuditSink()

    with pytest.raises(HTTPException) as error:
        make_repository(connection).deactivate_user(
            "usr_target", event=make_deactivation_event(), audit_sink=sink
        )

    assert error.value.status_code == 409
    assert connection.updated is False
    assert sink.calls == []
    assert connection.commits == 0
    assert connection.rollbacks == 1


def test_deactivation_audit_failure_rolls_back_status_change():
    connection = Connection(target=("Operador", "Ativo"))
    sink = AuditSink(fail=True)

    with pytest.raises(RuntimeError, match="audit insert failed"):
        make_repository(connection).deactivate_user(
            "usr_target", event=make_deactivation_event(), audit_sink=sink
        )

    assert connection.updated is True
    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closes == 1


def test_missing_user_cannot_be_deactivated_or_audited():
    connection = Connection(target=None)
    sink = AuditSink()

    with pytest.raises(HTTPException) as error:
        make_repository(connection).deactivate_user(
            "usr_missing",
            event=AuditEvent(
                actor_subject="google-subject-admin",
                action="usuarios:desativar",
                entity_type="usuario",
                entity_id="usr_missing",
            ),
            audit_sink=sink,
        )

    assert error.value.status_code == 404
    assert connection.updated is False
    assert sink.calls == []
    assert connection.rollbacks == 1
