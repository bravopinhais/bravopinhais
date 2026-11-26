from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.core.postgres_repositories import (
    PostgresFinanceiroRepository,
    PostgresPlanoContasRepository,
)
from app.modules.financeiro.schemas import FinanceiroTitulo
from app.modules.plano_contas.schemas import PlanoConta


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.rowcount = 1
        self.description = None

    def execute(self, sql, params=()):
        self.connection.calls.append((sql, params))
        if self.connection.error:
            error = self.connection.error
            self.connection.error = None
            raise error
        self.connection.rows = self.connection.next_rows
        self.rowcount = self.connection.next_rowcount

    def fetchall(self):
        return self.connection.rows

    def fetchone(self):
        return self.connection.rows[0] if self.connection.rows else None

    def close(self):
        self.connection.cursor_closed += 1


class FakeConnection:
    def __init__(self, rows=None, rowcount=1, error=None):
        self.next_rows = rows or []
        self.next_rowcount = rowcount
        self.error = error
        self.rows = []
        self.calls = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = 0
        self.cursor_closed = 0

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed += 1


def factory_for(connection):
    return lambda: connection


def test_plan_account_repository_maps_rows_and_commits():
    connection = FakeConnection(rows=[("pc_1", "1.1", "Receita", "Receita")])
    repository = PostgresPlanoContasRepository(factory_for(connection))

    result = repository.get("pc_1")

    assert result == PlanoConta(id="pc_1", codigo="1.1", nome="Receita", tipo="Receita")
    assert connection.calls[0][1] == ("pc_1",)
    assert connection.commits == 1
    assert connection.closed == connection.cursor_closed == 1


def test_finance_repository_converts_empty_account_to_null_and_decimal():
    connection = FakeConnection()
    repository = PostgresFinanceiroRepository(factory_for(connection))
    title = FinanceiroTitulo(
        id="fin_1", tipo="Receber", planoContaId="", historico="Cota", valor=Decimal("10.25")
    )

    repository.add(title.id, title)

    sql, params = connection.calls[0]
    assert "INSERT INTO bravo_shadow.financeiro" in sql
    assert params == ("fin_1", "Receber", None, "Cota", Decimal("10.25"))
    assert connection.commits == 1


def test_finance_repository_maps_null_account_to_legacy_empty_string():
    connection = FakeConnection(rows=[("fin_1", "Pagar", None, "Água", Decimal("8.50"))])
    repository = PostgresFinanceiroRepository(factory_for(connection))

    result = repository.get("fin_1")

    assert result.planoContaId == ""
    assert result.valor == Decimal("8.50")


def test_plan_account_delete_translates_foreign_key_conflict():
    class ForeignKeyViolation(Exception):
        sqlstate = "23503"

    connection = FakeConnection(error=ForeignKeyViolation("referenced"))
    repository = PostgresPlanoContasRepository(factory_for(connection))

    with pytest.raises(HTTPException) as error:
        repository.delete("pc_used")

    assert error.value.status_code == 409
    assert connection.rollbacks == 1
    assert connection.closed == 1


def test_missing_update_is_not_found():
    connection = FakeConnection(rowcount=0)
    repository = PostgresFinanceiroRepository(factory_for(connection))

    with pytest.raises(HTTPException) as error:
        repository.replace(
            "missing",
            FinanceiroTitulo(
                id="missing", tipo="Receber", planoContaId="", historico="Cota", valor=Decimal("1.00")
            ),
        )

    assert error.value.status_code == 404
