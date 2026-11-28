from datetime import date
from fastapi import HTTPException
import pytest

from app.core.postgres_inventory import (
    PostgresAcertosEstoqueRepository,
    PostgresEstoqueRepository,
)
from app.modules.acertos_estoque.schemas import Acerto
from app.modules.estoque.schemas import EstoqueItem


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.rowcount = 1

    def execute(self, sql, params=()):
        self.connection.calls.append((sql, params))
        if "SELECT quantidade" in sql:
            self.connection.row = self.connection.stock_row
        elif "SELECT 1 FROM bravo_shadow.acertos_estoque" in sql:
            self.connection.row = self.connection.movement_row
        elif sql.lstrip().startswith("SELECT"):
            self.connection.row = self.connection.rows[0] if self.connection.rows else None
        self.rowcount = self.connection.rowcount

    def fetchone(self):
        return self.connection.row

    def fetchall(self):
        return self.connection.rows

    def close(self):
        self.connection.cursor_closed += 1


class Connection:
    def __init__(self, *, stock_row=(5,), movement_row=None, rows=None, rowcount=1):
        self.stock_row = stock_row
        self.movement_row = movement_row
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


def test_stock_repository_maps_extended_origin_fields():
    connection = Connection(rows=[(
        "est_1", "Lâmpada", 7, 2, 20, "etq", "foto.jpg", "gzip",
        "Marca", "Linha", "Fabricante", date(2026, 11, 26),
        "Portaria", "un", 12.50, "Ativo", "Branco", "anexos/foto-1",
    )])
    repository = PostgresEstoqueRepository(factory(connection))

    item = repository.get("est_1")

    assert item == EstoqueItem(
        id="est_1", item="Lâmpada", quantidade=7, minimo=2, maximo=20,
        etiqueta="etq", fotoNome="foto.jpg", fotoCompactadaGzip="gzip",
        marca="Marca", linha="Linha", fabricante="Fabricante",
        dataCadastro="2026-11-26", setor="Portaria", unidade="un",
        valorUnitario=12.50, status="Ativo", cor="Branco",
        fotoPath="anexos/foto-1",
    )
    assert connection.commits == 1
    assert connection.closed == 1


def test_movement_updates_stock_and_inserts_history_in_one_transaction():
    connection = Connection(stock_row=(5,))
    repository = PostgresAcertosEstoqueRepository(factory(connection))
    movement = Acerto(
        id="ac_1", data="2026-11-26T10:00:00-03:00", tipo="Saída",
        produtoId="est_1", quantidade=2, motivo="Uso interno",
    )

    result = repository.register_movement(
        product_id="est_1", movement=movement, delta=-2,
    )

    assert result == movement
    assert len(connection.calls) == 3
    assert "FOR UPDATE" in connection.calls[0][0]
    assert connection.calls[1][1] == (3, "est_1")
    assert "INSERT INTO bravo_shadow.acertos_estoque" in connection.calls[2][0]
    assert connection.calls[2][1] == (
        "ac_1", movement.data, "Saída", "est_1", 2, "Uso interno", None,
    )
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closed == connection.cursor_closed == 1


def test_movement_with_insufficient_stock_rolls_back_without_inserting_history():
    connection = Connection(stock_row=(1,))
    repository = PostgresAcertosEstoqueRepository(factory(connection))
    movement = Acerto(
        id="ac_2", data="2026-11-26T10:00:00-03:00", tipo="Saída",
        produtoId="est_1", quantidade=2, motivo="Uso",
    )

    with pytest.raises(HTTPException) as error:
        repository.register_movement(
            product_id="est_1", movement=movement, delta=-2,
        )

    assert error.value.status_code == 409
    assert len(connection.calls) == 1
    assert connection.rollbacks == 1
    assert connection.commits == 0
    assert connection.closed == 1


def test_movement_for_missing_product_returns_404_and_rolls_back():
    connection = Connection(stock_row=None)
    repository = PostgresAcertosEstoqueRepository(factory(connection))
    movement = Acerto(
        id="ac_3", data="2026-11-26T10:00:00-03:00", tipo="Entrada",
        produtoId="missing", quantidade=1, motivo="Teste",
    )

    with pytest.raises(HTTPException) as error:
        repository.register_movement(
            product_id="missing", movement=movement, delta=1,
        )

    assert error.value.status_code == 404
    assert connection.rollbacks == 1
    assert connection.commits == 0



def test_stock_edit_preserves_balance_when_no_movement_exists():
    connection = Connection(stock_row=(5,), movement_row=None)
    repository = PostgresEstoqueRepository(factory(connection))
    item = EstoqueItem(
        id="est_1", item="Lâmpada", quantidade=8, minimo=2, maximo=20,
        etiqueta="", fotoNome="", fotoCompactadaGzip="", marca="Marca",
        linha="Linha", fabricante="Fábrica", dataCadastro="",
    )

    repository.replace("est_1", item)

    assert len(connection.calls) == 3
    assert "FOR UPDATE" in connection.calls[0][0]
    assert "SELECT 1 FROM bravo_shadow.acertos_estoque" in connection.calls[1][0]
    assert "UPDATE bravo_shadow.estoque" in connection.calls[2][0]
    assert connection.commits == 1
    assert connection.rollbacks == 0


def test_stock_edit_cannot_change_balance_after_movement_history_exists():
    connection = Connection(stock_row=(5,), movement_row=("ac_1",))
    repository = PostgresEstoqueRepository(factory(connection))
    item = EstoqueItem(
        id="est_1", item="Lâmpada", quantidade=8, minimo=2, maximo=20,
        etiqueta="", fotoNome="", fotoCompactadaGzip="", marca="Marca",
        linha="Linha", fabricante="Fábrica", dataCadastro="",
    )

    with pytest.raises(HTTPException) as error:
        repository.replace("est_1", item)

    assert error.value.status_code == 409
    assert len(connection.calls) == 2
    assert connection.rollbacks == 1
    assert connection.commits == 0


def test_postgres_movement_repository_blocks_replace_and_delete():
    row = ("ac_1", "2026-11-26T10:00:00-03:00", "Saída", "est_1", 1, "Uso", None)
    for operation in ("replace", "delete"):
        connection = Connection(rows=[row])
        repository = PostgresAcertosEstoqueRepository(factory(connection))
        with pytest.raises(HTTPException) as error:
            if operation == "replace":
                movement = Acerto(
                    id="ac_1", data=row[1], tipo="Saída", produtoId="est_1",
                    quantidade=1, motivo="Uso",
                )
                repository.replace("ac_1", movement)
            else:
                repository.delete("ac_1")
        assert error.value.status_code == 409
        assert len(connection.calls) == 1
        assert connection.calls[0][0].startswith("SELECT")


def test_postgres_movement_repository_returns_404_for_missing_immutable_record():
    connection = Connection(rows=[])
    repository = PostgresAcertosEstoqueRepository(factory(connection))
    with pytest.raises(HTTPException) as error:
        repository.delete("missing")
    assert error.value.status_code == 404



def test_stock_repository_preserves_fractional_quantities_and_legacy_metadata():
    from decimal import Decimal

    item = EstoqueItem(
        id="est_fraction", item="Produto fracionado",
        quantidade=Decimal("1.375"), minimo=Decimal("0.250"),
        maximo=Decimal("4.500"), unidade="kg", valorUnitario=Decimal("9.90"),
        setor="DML", status="Inativo", cor="Azul", fotoPath="anexos/item",
    )

    assert item.quantidade == Decimal("1.375")
    assert item.minimo == Decimal("0.250")
    assert item.maximo == Decimal("4.500")
    assert item.valorUnitario == Decimal("9.90")
    assert item.status == "Inativo"


class RecordingAuditSink:
    def __init__(self, fail=False):
        self.connection = None
        self.events = []
        self.fail = fail

    def append_in_transaction(self, connection, event):
        self.connection = connection
        if self.fail:
            raise RuntimeError("audit insert failed")
        self.events.append(event)


def test_audited_movement_commits_stock_history_and_audit_together():
    from app.core.audit import AuditEvent

    connection = Connection(stock_row=(5,))
    repository = PostgresAcertosEstoqueRepository(factory(connection))
    sink = RecordingAuditSink()
    movement = Acerto(
        id="ac_audited", data="2026-11-26T10:00:00-03:00", tipo="Saída",
        produtoId="est_1", quantidade=2, motivo="Uso interno",
    )
    event = AuditEvent(
        actor_subject="google-subject", action="acertos_estoque:create",
        entity_type="acerto_estoque", entity_id=movement.id,
        request_id="req-audited",
    )

    result = repository.register_movement_audited(
        product_id="est_1", movement=movement, delta=-2,
        event=event, audit_sink=sink,
    )

    assert result == movement
    assert sink.connection is connection
    assert sink.events == [event]
    assert len(connection.calls) == 3
    assert "FOR UPDATE" in connection.calls[0][0]
    assert "UPDATE bravo_shadow.estoque" in connection.calls[1][0]
    assert "INSERT INTO bravo_shadow.acertos_estoque" in connection.calls[2][0]
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closed == 1


def test_audited_movement_rolls_back_stock_and_history_when_audit_fails():
    from app.core.audit import AuditEvent

    connection = Connection(stock_row=(5,))
    repository = PostgresAcertosEstoqueRepository(factory(connection))
    sink = RecordingAuditSink(fail=True)
    movement = Acerto(
        id="ac_audit_fail", data="2026-11-26T10:00:00-03:00", tipo="Entrada",
        produtoId="est_1", quantidade=3, motivo="Reposição",
    )
    event = AuditEvent(
        actor_subject="google-subject", action="acertos_estoque:create",
        entity_type="acerto_estoque", entity_id=movement.id,
        request_id="req-audit-fail",
    )

    with pytest.raises(RuntimeError, match="audit insert failed"):
        repository.register_movement_audited(
            product_id="est_1", movement=movement, delta=3,
            event=event, audit_sink=sink,
        )

    assert sink.connection is connection
    assert len(connection.calls) == 3
    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closed == 1


def test_stock_create_audit_uses_same_transaction():
    from app.core.audit import AuditEvent

    connection = Connection()
    repository = PostgresEstoqueRepository(factory(connection))
    sink = RecordingAuditSink()
    item = EstoqueItem(id="est_audited", item="Produto auditado")
    event = AuditEvent(
        actor_subject="google-subject", action="estoque:create",
        entity_type="estoque", entity_id=item.id, request_id="req-stock",
    )

    repository.add_audited(item.id, item, event, sink)

    assert sink.connection is connection
    assert sink.events == [event]
    assert len(connection.calls) == 1
    assert connection.commits == 1
    assert connection.rollbacks == 0
    assert connection.closed == 1


def test_stock_audit_failure_rolls_back_create():
    from app.core.audit import AuditEvent

    connection = Connection()
    repository = PostgresEstoqueRepository(factory(connection))
    sink = RecordingAuditSink(fail=True)
    item = EstoqueItem(id="est_audit_fail", item="Produto auditado")
    event = AuditEvent(
        actor_subject="google-subject", action="estoque:create",
        entity_type="estoque", entity_id=item.id,
    )

    with pytest.raises(RuntimeError, match="audit insert failed"):
        repository.add_audited(item.id, item, event, sink)

    assert sink.connection is connection
    assert connection.commits == 0
    assert connection.rollbacks == 1
    assert connection.closed == 1


def test_stock_service_rejects_mutation_without_authenticated_actor_when_audited():
    from app.modules.estoque.schemas import EstoqueInput
    from app.modules.estoque.service import EstoqueService
    from app.core.repositories import InMemoryCollectionRepository

    service = EstoqueService(
        repository=InMemoryCollectionRepository(),
        audit_sink=object(),
    )

    with pytest.raises(HTTPException) as error:
        service.create(EstoqueInput(item="Produto sem ator"))

    assert error.value.status_code == 403
    assert service.list() == []


def test_adjustment_service_rejects_mutation_without_authenticated_actor_when_audited():
    from app.modules.acertos_estoque.schemas import AcertoInput
    from app.modules.acertos_estoque.service import AcertosEstoqueService
    from app.core.repositories import InMemoryCollectionRepository
    from app.modules.estoque.service import EstoqueService

    service = AcertosEstoqueService(
        repository=InMemoryCollectionRepository(),
        inventory_service=EstoqueService(),
        movement_repository=object(),
        audit_sink=object(),
    )

    with pytest.raises(HTTPException) as error:
        service.create(AcertoInput(
            tipo="Entrada", produtoId="est_1", quantidade=1, motivo="Teste",
        ))

    assert error.value.status_code == 403
    assert service.list() == []
