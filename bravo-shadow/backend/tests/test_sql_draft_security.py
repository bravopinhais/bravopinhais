from pathlib import Path
import re


SQL_PATH = Path(__file__).resolve().parents[2] / "docs" / "sql-piloto-financeiro.sql"


def _sql() -> str:
    return SQL_PATH.read_text(encoding="utf-8")


def test_every_declared_table_has_rls_and_client_grants_revoked():
    sql = _sql()
    tables = set(re.findall(
        r"create table if not exists bravo_shadow\.(\w+)", sql, re.IGNORECASE
    ))
    rls = set(re.findall(
        r"alter table bravo_shadow\.(\w+) enable row level security",
        sql,
        re.IGNORECASE,
    ))
    revoked = set(re.findall(
        r"revoke all on table bravo_shadow\.(\w+) from public, anon, authenticated, service_role",
        sql,
        re.IGNORECASE,
    ))

    assert len(tables) == 15
    assert rls == tables
    assert revoked == tables


def test_financial_and_inventory_integrity_constraints_are_present():
    sql = _sql().lower()

    assert "valor numeric(14, 2) not null" in sql
    assert "saldo numeric(14, 2) not null default 0" in sql
    assert "foreign key (plano_conta_id)" in sql
    assert "on delete restrict" in sql
    assert "check (quantidade > 0)" in sql
    assert "foreign key (produto_id)" in sql
    assert "foreign key (motivo_id)" in sql
    assert "lower(codigo)" in sql
    assert "lower(btrim(email))" in sql


def test_stock_movement_history_is_marked_immutable_for_api_role():
    sql = _sql().lower()

    assert "não deve receber" in sql
    assert "delete em bravo_shadow.acertos_estoque" in sql
    assert "movimentos compensatórios" in sql
