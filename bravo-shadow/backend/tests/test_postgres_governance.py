import pytest

from app.core.postgres_governance import (
    PostgresCondominioRepository,
    PostgresConselheirosRepository,
)
from app.core.storage import build_storage_services
from app.modules.conselheiros.schemas import Conselheiro


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.rowcount = connection.rowcount

    def execute(self, sql, params=()):
        self.connection.calls.append((sql, params))
        if sql.lstrip().startswith("SELECT"):
            self.connection.row = self.connection.row_value

    def fetchone(self):
        return self.connection.row

    def fetchall(self):
        return self.connection.rows

    def close(self):
        self.connection.cursor_closed += 1


class Connection:
    def __init__(self, *, row=None, rows=None, rowcount=1):
        self.row_value = row
        self.row = None
        self.rows = rows or []
        self.rowcount = rowcount
        self.calls = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0
        self.cursor_closed = 0

    def cursor(self):
        return Cursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed += 1


def factory(connection):
    return lambda: connection


def test_condominio_repository_maps_all_legacy_fields():
    values = tuple(f"valor_{index}" for index in range(17))
    connection = Connection(row=values)
    repository = PostgresCondominioRepository(factory(connection))

    item = repository.get("singleton")

    assert item["nome"] == "valor_0"
    assert item["razaoSocial"] == "valor_2"
    assert item["copelAreasComuns"] == "valor_14"
    assert item["sanepar"] == "valor_16"
    assert '"razaoSocial"' in connection.calls[0][0]
    assert connection.commits == 1


def test_conselheiros_repository_maps_and_persists_contract_fields():
    connection = Connection(row=("cons_1", "Ana", "Síndica", "A-101", "41999990000"))
    repository = PostgresConselheirosRepository(factory(connection))

    item = repository.get("cons_1")

    assert item == Conselheiro(
        id="cons_1", nome="Ana", cargo="Síndica",
        BlocoAp="A-101", telefone="41999990000",
    )
    repository.add("cons_2", item)
    assert connection.calls[1][1] == ("cons_2", "Ana", "Síndica", "A-101", "41999990000")
    assert connection.commits == 2


def test_postgres_storage_wires_governance_repositories_without_connecting():
    def unexpected_connection():
        raise AssertionError("A conexão não deve abrir durante a montagem.")

    services = build_storage_services("postgres", connection_factory=unexpected_connection)

    assert isinstance(services.condominio.repository._repository, PostgresCondominioRepository)
    assert isinstance(services.conselheiros.repository._repository, PostgresConselheirosRepository)



def test_empty_condominio_patch_checks_existence_without_invalid_update():
    connection = Connection(row=("Bravo",) + tuple("" for _ in range(16)))
    repository = PostgresCondominioRepository(factory(connection))

    repository.replace("singleton", {})

    assert len(connection.calls) == 1
    assert connection.calls[0][0].startswith("SELECT")
    assert connection.commits == 1


def test_empty_condominio_patch_still_returns_not_found_for_missing_record():
    connection = Connection(row=None)
    repository = PostgresCondominioRepository(factory(connection))

    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as error:
        repository.replace("missing", {})

    assert error.value.status_code == 404
    assert len(connection.calls) == 1
    assert connection.commits == 1


from app.core.audit import AuditEvent


class GovernanceAuditSink:
    def __init__(self, *, fail=False):
        self.fail = fail
        self.events = []
        self.connection = None

    def append_in_transaction(self, connection, event):
        self.connection = connection
        if self.fail:
            raise RuntimeError("audit insert failed")
        self.events.append(event)


@pytest.mark.parametrize("operation", ["add", "replace", "delete"])
def test_council_mutation_and_audit_share_transaction(operation):
    connection = Connection()
    sink = GovernanceAuditSink()
    repository = PostgresConselheirosRepository(factory(connection))
    item = Conselheiro(id="cons_1", nome="Ana", cargo="Síndica", BlocoAp="A-101", telefone="41999990000")
    event = AuditEvent(actor_subject="google-subject", action="conselheiros:test", entity_type="conselheiro", entity_id="cons_1", request_id="req_test")

    if operation == "add":
        repository.add_audited(item.id, item, event, sink)
    elif operation == "replace":
        repository.replace_audited(item.id, item, event, sink)
    else:
        repository.delete_audited(item.id, event, sink)

    assert len(connection.calls) == 1
    assert "bravo_shadow.conselheiros" in connection.calls[0][0]
    assert sink.connection is connection
    assert sink.events == [event]
    assert connection.commits == 1
    assert connection.rollbacks == 0


@pytest.mark.parametrize("operation", ["add", "replace", "delete"])
def test_council_audit_failure_rolls_back_mutation(operation):
    import pytest

    connection = Connection()
    sink = GovernanceAuditSink(fail=True)
    repository = PostgresConselheirosRepository(factory(connection))
    item = Conselheiro(id="cons_1", nome="Ana", cargo="Síndica", BlocoAp="A-101", telefone="41999990000")

    with pytest.raises(RuntimeError, match="audit insert failed"):
        if operation == "add":
            repository.add_audited(item.id, item, object(), sink)
        elif operation == "replace":
            repository.replace_audited(item.id, item, object(), sink)
        else:
            repository.delete_audited(item.id, object(), sink)

    assert connection.commits == 0
    assert connection.rollbacks == 1


from app.core.audit import AuditEvent


@pytest.mark.parametrize("patch_fields", [{"nome": "Residencial"}, {}, {"cidade": "Curitiba", "uf": "PR"}])
def test_condominio_patch_and_audit_share_transaction(patch_fields):
    connection = Connection()
    sink = GovernanceAuditSink()
    repository = PostgresCondominioRepository(factory(connection))
    event = AuditEvent(
        actor_subject="google-subject", action="condominio:update",
        entity_type="condominio", entity_id="singleton", request_id="req_condo",
    )

    repository.replace_audited("singleton", patch_fields, event, sink)

    assert len(connection.calls) == 1
    sql, params = connection.calls[0]
    assert sql.startswith("INSERT INTO bravo_shadow.condominio")
    assert "ON CONFLICT (id)" in sql
    assert params[0] == "singleton"
    assert sink.connection is connection
    assert sink.events == [event]
    assert connection.commits == 1
    assert connection.rollbacks == 0


def test_condominio_audit_failure_rolls_back_patch():
    connection = Connection()
    sink = GovernanceAuditSink(fail=True)
    repository = PostgresCondominioRepository(factory(connection))
    event = AuditEvent(
        actor_subject="google-subject", action="condominio:update",
        entity_type="condominio", entity_id="singleton", request_id="req_condo",
    )

    with pytest.raises(RuntimeError, match="audit insert failed"):
        repository.replace_audited("singleton", {"nome": "Residencial"}, event, sink)

    assert connection.commits == 0
    assert connection.rollbacks == 1
