"""Static closure checks between PostgreSQL adapters and unexecuted SQL drafts.

These tests inspect source text only. They do not parse with PostgreSQL, connect,
execute SQL, or establish that a draft is deployable.
"""
from __future__ import annotations

from pathlib import Path
import re

from app.core.migration_apply_store_postgres import (
    REQUIRED_TARGET_COLUMNS,
    TARGET_COLUMNS,
)
from app.core.migration_target_payload_contract import (
    DATE_COLUMNS,
    ENUMS,
    NULLABLE_COLUMNS,
    NUMERIC_COLUMNS,
    TIMESTAMPTZ_COLUMNS,
)

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
CORE = ROOT / "backend" / "app" / "core"


def _read(path: str) -> str:
    return (DOCS / path).read_text(encoding="utf-8")


def _table_body(sql: str, table: str) -> str:
    match = re.search(
        rf"create\s+table\s+if\s+not\s+exists\s+bravo_shadow\.{re.escape(table)}\s*\((.*?)\n\);",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, f"DDL table not found: {table}"
    return match.group(1)


def _columns(body: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in body.splitlines():
        line = line.strip().rstrip(",")
        if not line or line.upper().startswith(("CONSTRAINT ", "PRIMARY ", "UNIQUE ", "CHECK ", "FOREIGN ")):
            continue
        match = re.match(r'"([^"]+)"\s+(.+)$|([A-Za-z_][A-Za-z0-9_]*)\s+(.+)$', line)
        if match:
            name = match.group(1) or match.group(3)
            declaration = match.group(2) or match.group(4)
            found[name] = declaration
    return found


def test_every_adapter_target_allowlist_matches_a_real_sql_table_and_column():
    sql = _read("sql-piloto-financeiro.sql")
    assert set(TARGET_COLUMNS) == {
        "formas_monetarias", "plano_contas", "financeiro", "moradores",
        "fornecedores", "empregados", "contas_bancarias", "condominio",
        "conselheiros", "usuarios", "estoque", "categorias",
        "motivos_acerto", "documentos", "acertos_estoque",
    }
    for table, allowed in TARGET_COLUMNS.items():
        columns = _columns(_table_body(sql, table))
        assert set(allowed) <= set(columns), f"{table}: allowlist has missing SQL columns"
        # These are DB-managed metadata columns and must never be supplied by importer.
        importer_columns = set(columns) - {"created_at", "updated_at", "version"}
        assert set(allowed) == importer_columns, f"{table}: target allowlist drift"


def test_required_target_fields_equal_not_null_without_default_ddl_columns():
    sql = _read("sql-piloto-financeiro.sql")
    for table, allowed in TARGET_COLUMNS.items():
        columns = _columns(_table_body(sql, table))
        expected = {
            name for name, declaration in columns.items()
            if "NOT NULL" in declaration.upper()
            and not re.search(r"\bDEFAULT\b", declaration, re.IGNORECASE)
            and name != "id"
        }
        assert set(REQUIRED_TARGET_COLUMNS[table]) == expected, table
        assert set(REQUIRED_TARGET_COLUMNS[table]) <= set(allowed)


def test_python_value_type_contract_matches_sql_numeric_date_and_timestamp_types():
    sql = _read("sql-piloto-financeiro.sql")
    all_columns = {
        (table, name): declaration
        for table in TARGET_COLUMNS
        for name, declaration in _columns(_table_body(sql, table)).items()
    }
    for key, (precision, scale, rule) in NUMERIC_COLUMNS.items():
        declaration = all_columns[key].lower()
        if rule == "finite_float":
            assert re.match(r"double\s+precision\b", declaration), key
        else:
            assert re.match(rf"numeric\s*\(\s*{precision}\s*,\s*{scale}\s*\)", declaration), key
    for key in DATE_COLUMNS:
        assert re.match(r"date\b", all_columns[key].lower()), key
    for key in TIMESTAMPTZ_COLUMNS:
        assert re.match(r"timestamptz\b", all_columns[key].lower()), key


def test_nullable_target_fields_are_exactly_the_nullable_fields_in_sql():
    sql = _read("sql-piloto-financeiro.sql")
    all_columns = {
        (table, name): declaration
        for table in TARGET_COLUMNS
        for name, declaration in _columns(_table_body(sql, table)).items()
    }
    actual_nullable = {
        key for key, declaration in all_columns.items()
        if key[1] != "id" and "NOT NULL" not in declaration.upper()
    }
    assert NULLABLE_COLUMNS == actual_nullable


def test_enum_contract_literals_match_sql_check_constraints():
    sql = _read("sql-piloto-financeiro.sql")
    all_columns = {
        (table, name): declaration
        for table in TARGET_COLUMNS
        for name, declaration in _columns(_table_body(sql, table)).items()
    }
    for (table, column), expected in ENUMS.items():
        declaration = all_columns[(table, column)]
        check = re.search(
            rf"check\s*\(\s*{re.escape(column)}\s+in\s*\(([^)]*)\)\s*\)",
            _table_body(sql, table),
            re.IGNORECASE,
        )
        assert check, (table, column)
        actual = set(re.findall(r"'([^']+)'", check.group(1)))
        assert actual == expected, (table, column)


def test_provenance_adapter_columns_and_identity_constraints_match_control_ddl():
    ddl = _read("sql-controle-lotes-importacao-rascunho.sql")
    adapter = (CORE / "migration_source_records_postgres.py").read_text(encoding="utf-8")
    columns = set(_columns(_table_body(ddl, "migration_source_records")))
    used = {
        "source_system", "source_collection", "legacy_id",
        "destination_collection", "destination_id", "source_record_hash",
        "first_batch_id", "last_verified_batch_id",
    }
    assert used <= columns
    for column in used:
        assert re.search(rf"\b{column}\b", adapter)
    body = _table_body(ddl, "migration_source_records")
    assert re.search(
        r"primary\s+key\s*\(\s*source_system\s*,\s*source_collection\s*,\s*legacy_id\s*\)",
        body, re.IGNORECASE,
    )
    assert re.search(
        r"unique\s*\(\s*destination_collection\s*,\s*destination_id\s*\)",
        body, re.IGNORECASE,
    )
    assert re.search(
        r"check\s*\(\s*length\s*\(\s*btrim\(\s*source_system\s*\)\s*\)\s*>\s*0",
        body, re.IGNORECASE,
    )
    assert re.search(
        r"check\s*\(\s*source_record_hash\s*~\s*'\^\[0-9a-f\]\{64\}\

def test_authenticated_audit_insert_matches_all_required_sql_columns():
    ddl = _read("sql-auditoria-rascunho.sql")
    adapter = (CORE / "migration_apply_store_postgres.py").read_text(encoding="utf-8")
    columns = set(_columns(_table_body(ddl, "audit_events")))
    used = {
        "event_id", "occurred_at", "actor_subject", "action",
        "entity_type", "entity_id", "outcome", "request_id",
    }
    assert columns == used
    assert re.search(
        r"INSERT\s+INTO\s+bravo_shadow\.audit_events\s*\((.*?)\)\s*VALUES",
        adapter, re.IGNORECASE | re.DOTALL,
    )


def test_apply_authorization_and_lifecycle_fields_match_control_ddl():
    batch_ddl = _read("sql-controle-lotes-importacao-rascunho.sql")
    execution_ddl = _read("sql-execucao-aprovacao-apply-rascunho.sql")
    authorization = (CORE / "migration_apply_authorization_postgres.py").read_text(encoding="utf-8")
    transaction = (CORE / "migration_transaction.py").read_text(encoding="utf-8")
    batch_columns = set(_columns(_table_body(batch_ddl, "migration_batches")))
    execution_columns = set(_columns(_table_body(execution_ddl, "migration_executions")))
    approval_columns = set(_columns(_table_body(execution_ddl, "migration_apply_approvals")))
    assert {"batch_id", "manifest_hash", "source_system", "environment", "status", "approved_manifest_hash"} <= batch_columns
    assert {"execution_id", "batch_id", "manifest_hash", "plan_sha256", "environment", "status"} <= execution_columns
    assert {"execution_id", "batch_id", "manifest_hash", "plan_sha256", "decision", "reviewer_subject"} <= approval_columns
    for token in ("migration_batches", "migration_executions", "migration_apply_approvals", "FOR UPDATE"):
        assert token.lower() in authorization.lower()
    for token in ("status = 'applying'", "status = 'applied'", "finished_at", "started_at"):
        assert token in transaction


def test_lifecycle_states_written_by_coordinator_are_allowed_by_both_check_constraints():
    batch_ddl = _table_body(_read("sql-controle-lotes-importacao-rascunho.sql"), "migration_batches")
    execution_ddl = _table_body(_read("sql-execucao-aprovacao-apply-rascunho.sql"), "migration_executions")
    for status in ("approved", "applying", "applied"):
        assert f"'{status}'" in batch_ddl
        assert f"'{status}'" in execution_ddl


def test_target_only_foreign_keys_are_explicitly_not_claimed_as_legacy_mappings():
    sql = _read("sql-piloto-financeiro.sql").lower()
    reconciliation = (CORE / "migration_reference_reconciliation.py").read_text(encoding="utf-8")
    assert "references bravo_shadow.categorias (id)" in sql
    assert "references bravo_shadow.motivos_acerto (id)" in sql
    assert "documentos_categoria" not in reconciliation
    assert "acertos_estoque_motivo" not in reconciliation
",
        body, re.IGNORECASE,
    )
    assert re.search(
        r"foreign\s+key\s*\(\s*first_batch_id\s*,\s*source_system\s*\)",
        body, re.IGNORECASE,
    )
    assert re.search(
        r"foreign\s+key\s*\(\s*last_verified_batch_id\s*,\s*source_system\s*\)",
        body, re.IGNORECASE,
    )


def test_authenticated_audit_insert_matches_all_required_sql_columns():
    ddl = _read("sql-auditoria-rascunho.sql")
    adapter = (CORE / "migration_apply_store_postgres.py").read_text(encoding="utf-8")
    columns = set(_columns(_table_body(ddl, "audit_events")))
    used = {
        "event_id", "occurred_at", "actor_subject", "action",
        "entity_type", "entity_id", "outcome", "request_id",
    }
    assert columns == used
    assert re.search(
        r"INSERT\s+INTO\s+bravo_shadow\.audit_events\s*\((.*?)\)\s*VALUES",
        adapter, re.IGNORECASE | re.DOTALL,
    )


def test_apply_authorization_and_lifecycle_fields_match_control_ddl():
    batch_ddl = _read("sql-controle-lotes-importacao-rascunho.sql")
    execution_ddl = _read("sql-execucao-aprovacao-apply-rascunho.sql")
    authorization = (CORE / "migration_apply_authorization_postgres.py").read_text(encoding="utf-8")
    transaction = (CORE / "migration_transaction.py").read_text(encoding="utf-8")
    batch_columns = set(_columns(_table_body(batch_ddl, "migration_batches")))
    execution_columns = set(_columns(_table_body(execution_ddl, "migration_executions")))
    approval_columns = set(_columns(_table_body(execution_ddl, "migration_apply_approvals")))
    assert {"batch_id", "manifest_hash", "source_system", "environment", "status", "approved_manifest_hash"} <= batch_columns
    assert {"execution_id", "batch_id", "manifest_hash", "plan_sha256", "environment", "status"} <= execution_columns
    assert {"execution_id", "batch_id", "manifest_hash", "plan_sha256", "decision", "reviewer_subject"} <= approval_columns
    for token in ("migration_batches", "migration_executions", "migration_apply_approvals", "FOR UPDATE"):
        assert token.lower() in authorization.lower()
    for token in ("status = 'applying'", "status = 'applied'", "finished_at", "started_at"):
        assert token in transaction


def test_lifecycle_states_written_by_coordinator_are_allowed_by_both_check_constraints():
    batch_ddl = _table_body(_read("sql-controle-lotes-importacao-rascunho.sql"), "migration_batches")
    execution_ddl = _table_body(_read("sql-execucao-aprovacao-apply-rascunho.sql"), "migration_executions")
    for status in ("approved", "applying", "applied"):
        assert f"'{status}'" in batch_ddl
        assert f"'{status}'" in execution_ddl


def test_target_only_foreign_keys_are_explicitly_not_claimed_as_legacy_mappings():
    sql = _read("sql-piloto-financeiro.sql").lower()
    reconciliation = (CORE / "migration_reference_reconciliation.py").read_text(encoding="utf-8")
    assert "references bravo_shadow.categorias (id)" in sql
    assert "references bravo_shadow.motivos_acerto (id)" in sql
    assert "documentos_categoria" not in reconciliation
    assert "acertos_estoque_motivo" not in reconciliation
