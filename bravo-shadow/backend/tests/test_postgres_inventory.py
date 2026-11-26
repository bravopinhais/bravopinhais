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
    def __init__(self, *, stock_row=(5,), rows=None, rowcount=1):
        self.stock_row = stock_row
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
    )])
    repository = PostgresEstoqueRepository(factory(connection))

    item = repository.get("est_1")

    assert item == EstoqueItem(
        id="est_1", item="Lâmpada", quantidade=7, minimo=2, maximo=20,
        etiqueta="etq", fotoNome="foto.jpg", fotoCompactadaGzip="gzip",
        marca="Marca", linha="Linha", fabricante="Fabricante",
        dataCadastro="2026-11-26",
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
