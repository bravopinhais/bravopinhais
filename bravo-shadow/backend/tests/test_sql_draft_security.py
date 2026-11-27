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


def test_schema_access_is_revoked_from_public_and_supabase_api_roles():
    sql = re.sub(r"--[^\n]*", "", _sql()).lower()

    for role in ("public", "anon", "authenticated", "service_role"):
        assert f"revoke all on schema bravo_shadow from {role};" in sql


def test_draft_does_not_create_grants_or_permissive_policies():
    sql = re.sub(r"--[^\n]*", "", _sql()).lower()

    assert not re.search(r"\bgrant\s+", sql)
    assert not re.search(r"\bcreate\s+policy\s+", sql)
    assert len(re.findall(r"alter table bravo_shadow\.\w+ enable row level security", sql)) == 15


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


def test_plan_account_case_insensitive_unique_index_is_in_the_unapplied_draft():
    sql = _sql().lower()

    assert "create unique index if not exists plano_contas_codigo_ci_uidx" in sql
    assert "on bravo_shadow.plano_contas (lower(codigo))" in sql
    assert "rascunho de sql" in sql
    assert "ainda não é uma migration executável" in sql


def test_stock_movement_history_is_marked_immutable_for_api_role():
    sql = _sql().lower()

    assert "não deve receber" in sql
    assert "delete em bravo_shadow.acertos_estoque" in sql
    assert "movimentos compensatórios" in sql

AUDIT_SQL_PATH = Path(__file__).resolve().parents[2] / "docs" / "sql-auditoria-rascunho.sql"


def _audit_sql() -> str:
    return AUDIT_SQL_PATH.read_text(encoding="utf-8")


def test_audit_sql_draft_enables_and_forces_rls_without_opening_access():
    sql = re.sub(r"--[^\n]*", "", _audit_sql()).lower()

    assert "alter table bravo_shadow.audit_events enable row level security;" in sql
    assert "alter table bravo_shadow.audit_events force row level security;" in sql

    for role in ("public", "anon", "authenticated", "service_role"):
        assert f"revoke all on table bravo_shadow.audit_events from {role};" in sql


def test_audit_sql_draft_has_no_grants_or_policies():
    sql = re.sub(r"--[^\n]*", "", _audit_sql()).lower()

    assert not re.search(r"\bgrant\s+", sql)
    assert not re.search(r"\bcreate\s+policy\s+", sql)
    assert "create table if not exists bravo_shadow.audit_events" in sql
    assert "outcome in ('success', 'denied', 'failure')" in sql



INSPECTION_SQL_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "verificar-privilegios-rls-somente-leitura.sql"
)


def _inspection_sql() -> str:
    return INSPECTION_SQL_PATH.read_text(encoding="utf-8")


def test_postgres_inspection_script_is_explicitly_read_only():
    sql = re.sub(r"--[^\n]*", "", _inspection_sql()).strip()

    assert re.search(r"^begin\s+read\s+only\s*;", sql, re.IGNORECASE)
    statements = [statement.strip() for statement in sql.split(";") if statement.strip()]
    assert statements
    for statement in statements:
        assert re.match(
            r"^(?:BEGIN\s+READ\s+ONLY|SELECT|COMMIT)\b",
            statement,
            re.IGNORECASE,
        ), f"Unexpected non-read-only SQL statement: {statement[:80]}"


def test_postgres_inspection_script_covers_effective_security_catalogs():
    sql = re.sub(r"--[^\n]*", "", _inspection_sql()).lower()

    for required in (
        "from pg_roles",
        "from pg_auth_members",
        "from pg_class",
        "from pg_policies",
        "information_schema.role_table_grants",
        "has_table_privilege",
        "has_schema_privilege",
        "has_sequence_privilege",
        "has_function_privilege",
        "aclexplode",
    ):
        assert required in sql
