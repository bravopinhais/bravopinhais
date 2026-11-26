from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.core.postgres_repositories import (
    PostgresFinanceiroRepository,\n    PostgresFormasMonetariasRepository,
    PostgresPlanoContasRepository,
)
from app.modules.formas_monetarias.schemas import FormaMonetaria\nfrom app.modules.financeiro.schemas import FinanceiroTitulo
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
    connection = FakeConnection(rows=[("pc_1", "1.1", "Receita", "Receita", 3)])
    repository = PostgresPlanoContasRepository(factory_for(connection))

    result = repository.get("pc_1")

    assert result == PlanoConta(id="pc_1", codigo="1.1", nome="Receita", tipo="Receita", version=3)
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
    connection = FakeConnection(rows=[("fin_1", "Pagar", None, "Água", Decimal("8.50"), 6)])
    repository = PostgresFinanceiroRepository(factory_for(connection))

    result = repository.get("fin_1")

    assert result.planoContaId == ""
    assert result.valor == Decimal("8.50")
    assert result.version == 6


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


def test_plan_account_update_requires_matching_version():
    connection = FakeConnection(rowcount=1)
    repository = PostgresPlanoContasRepository(factory_for(connection))
    item = PlanoConta(id="pc_1", codigo="1.1", nome="Atualizada", tipo="Receita")

    new_version = repository.replace_if_version("pc_1", item, expected_version=4)

    sql, params = connection.calls[0]
    assert "WHERE id = %s AND version = %s" in sql
    assert params == ("1.1", "Atualizada", "Receita", "pc_1", 4)
    assert new_version == 5
    assert connection.commits == 1


def test_finance_update_rejects_stale_version_with_conflict():
    connection = FakeConnection(rows=[(8,)], rowcount=0)
    repository = PostgresFinanceiroRepository(factory_for(connection))
    item = FinanceiroTitulo(
        id="fin_1", tipo="Receber", planoContaId="", historico="Atualizado", valor=Decimal("25.00")
    )

    with pytest.raises(HTTPException) as error:
        repository.replace_if_version("fin_1", item, expected_version=7)

    assert error.value.status_code == 409
    assert "alterado por outra operação" in error.value.detail
    assert "SELECT version FROM bravo_shadow.financeiro" in connection.calls[1][0]
    assert connection.rollbacks == 1
    assert connection.closed == 1


def test_finance_update_with_version_returns_not_found_for_missing_record():
    connection = FakeConnection(rows=[], rowcount=0)
    repository = PostgresFinanceiroRepository(factory_for(connection))
    item = FinanceiroTitulo(
        id="missing", tipo="Receber", planoContaId="", historico="Cota", valor=Decimal("1.00")
    )

    with pytest.raises(HTTPException) as error:
        repository.replace_if_version("missing", item, expected_version=1)

    assert error.value.status_code == 404
    assert connection.rollbacks == 1
    assert connection.closed == 1


def test_finance_create_translates_missing_plan_account_reference():
    class ForeignKeyViolation(Exception):
        sqlstate = "23503"

    connection = FakeConnection(error=ForeignKeyViolation("missing account"))
    repository = PostgresFinanceiroRepository(factory_for(connection))
    item = FinanceiroTitulo(
        id="fin_2", tipo="Receber", planoContaId="pc_missing",
        historico="Cota", valor=Decimal("10.00"),
    )

    with pytest.raises(HTTPException) as error:
        repository.add(item.id, item)

    assert error.value.status_code == 409
    assert "Plano de Contas" in error.value.detail
    assert connection.rollbacks == 1
    assert connection.closed == 1


def test_finance_update_translates_missing_plan_account_reference():
    class ForeignKeyViolation(Exception):
        sqlstate = "23503"

    connection = FakeConnection(error=ForeignKeyViolation("missing account"))
    repository = PostgresFinanceiroRepository(factory_for(connection))
    item = FinanceiroTitulo(
        id="fin_2", tipo="Receber", planoContaId="pc_missing",
        historico="Cota", valor=Decimal("10.00"),
    )

    with pytest.raises(HTTPException) as error:
        repository.replace_if_version(item.id, item, expected_version=1)

    assert error.value.status_code == 409
    assert "Plano de Contas" in error.value.detail
    assert connection.rollbacks == 1
    assert connection.closed == 1



def test_monetary_forms_repository_crud_uses_legacy_fields():
    connection = FakeConnection(
        rows=[("fm_1", "Boleto", 2.5)]
    )
    repository = PostgresFormasMonetariasRepository(factory_for(connection))

    item = repository.get("fm_1")
    assert item == FormaMonetaria(id="fm_1", nome="Boleto", multaPct=2.5)
    assert "SELECT id, nome, multa_pct" in connection.calls[0][0]

    repository.add("fm_2", FormaMonetaria(id="fm_2", nome="PIX", multaPct=0.0))
    assert connection.calls[1][1] == ("fm_2", "PIX", 0.0)

    repository.replace("fm_2", FormaMonetaria(id="fm_2", nome="Dinheiro", multaPct=-1.0))
    assert "version = version + 1" in connection.calls[2][0]
    assert connection.calls[2][1] == ("Dinheiro", -1.0, "fm_2")

    repository.delete("fm_2")
    assert "DELETE FROM bravo_shadow.formas_monetarias" in connection.calls[3][0]
    assert connection.commits == 4
    assert connection.closed == 4


def test_monetary_forms_repository_missing_update_and_delete_return_404():
    connection = FakeConnection(rowcount=0)
    repository = PostgresFormasMonetariasRepository(factory_for(connection))
    item = FormaMonetaria(id="missing", nome="Boleto", multaPct=2.0)

    with pytest.raises(HTTPException) as update_error:
        repository.replace("missing", item)
    assert update_error.value.status_code == 404

    with pytest.raises(HTTPException) as delete_error:
        repository.delete("missing")
    assert delete_error.value.status_code == 404
