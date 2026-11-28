from __future__ import annotations

import pytest

from app.core.audit import AuditEvent
from app.core.postgres_cadastros import (
    PostgresEmpregadosRepository,
    PostgresFornecedoresRepository,
    PostgresMoradoresRepository,
)
from app.modules.empregados.schemas import Empregado
from app.modules.fornecedores.schemas import Fornecedor
from app.modules.moradores.schemas import Morador


class FakeCursor:
    def __init__(self):
        self.rowcount = 1
        self.statements = []
        self.closed = False

    def execute(self, sql, params):
        self.statements.append((sql, params))

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()
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


class RecordingAuditSink:
    def __init__(self, *, fail=False):
        self.connection = None
        self.events = []
        self.fail = fail

    def append_in_transaction(self, connection, event):
        self.connection = connection
        self.events.append(event)
        if self.fail:
            raise RuntimeError("falha sintética de auditoria")


def _cases():
    resident = Morador(id="mor_shadow_test", bloco="1", apartamento="101", nome="Morador Teste")
    supplier = Fornecedor(id="for_shadow_test", cnpj="12.345.678/0001-90", razaoSocial="Fornecedor Teste")
    employee = Empregado(id="emp_shadow_test", nome="Empregado Teste", cargo="Zelador")
    return [
        (PostgresMoradoresRepository, resident, "mor_shadow_test"),
        (PostgresFornecedoresRepository, supplier, "for_shadow_test"),
        (PostgresEmpregadosRepository, employee, "emp_shadow_test"),
    ]


@pytest.mark.parametrize("repository_type,item,item_id", _cases())
@pytest.mark.parametrize("operation_name", ["add_audited", "replace_audited", "delete_audited"])
def test_cadastro_audited_mutations_share_connection_and_commit(repository_type, item, item_id, operation_name):
    connection = FakeConnection()
    repository = repository_type(lambda: connection)
    sink = RecordingAuditSink()
    event = AuditEvent(
        actor_subject="google-test-subject",
        action=f"{repository_type.__name__}:{operation_name}",
        entity_type="cadastro",
        entity_id=item_id,
        request_id="request-test",
    )

    operation = getattr(repository, operation_name)
    if operation_name == "add_audited":
        operation(item, event, sink)
    elif operation_name == "replace_audited":
        operation(item_id, item, event, sink)
    else:
        operation(item_id, event, sink)

    assert sink.connection is connection
    assert sink.events == [event]
    assert len(connection.cursor_instance.statements) == 1
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closes == 1
    assert connection.cursor_instance.closed is True


@pytest.mark.parametrize("repository_type,item,item_id", _cases())
@pytest.mark.parametrize("operation_name", ["add_audited", "replace_audited", "delete_audited"])
def test_cadastro_audit_failure_rolls_back_business_mutation(repository_type, item, item_id, operation_name):
    connection = FakeConnection()
    repository = repository_type(lambda: connection)
    sink = RecordingAuditSink(fail=True)
    event = AuditEvent(
        actor_subject="google-test-subject",
        action=f"{repository_type.__name__}:{operation_name}",
        entity_type="cadastro",
        entity_id=item_id,
        request_id="request-test",
    )

    operation = getattr(repository, operation_name)
    with pytest.raises(RuntimeError, match="falha sintética"):
        if operation_name == "add_audited":
            operation(item, event, sink)
        elif operation_name == "replace_audited":
            operation(item_id, item, event, sink)
        else:
            operation(item_id, event, sink)

    assert sink.connection is connection
    assert len(connection.cursor_instance.statements) == 1
    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closes == 1
    assert connection.cursor_instance.closed is True
