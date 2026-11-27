"""Static safety checks for the unexecuted migration-control SQL draft.

These tests do not parse or execute PostgreSQL SQL. They guard the documented
contract until a reviewed local migration and disposable-PostgreSQL suite exist.
"""
from __future__ import annotations

from pathlib import Path
import re


SQL_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "sql-controle-lotes-importacao-rascunho.sql"
)


def _sql() -> str:
    return SQL_PATH.read_text(encoding="utf-8")


def test_draft_declares_only_batch_and_source_provenance_tables():
    sql = _sql().lower()
    creates = re.findall(
        r"create\s+table\s+if\s+not\s+exists\s+([a-z0-9_.]+)",
        sql,
    )

    assert creates == [
        "bravo_shadow.migration_batches",
        "bravo_shadow.migration_source_records",
    ]


def test_source_identity_and_destination_are_unique():
    sql = _sql().lower()

    assert re.search(
        r"primary\s+key\s*\(\s*source_system\s*,\s*source_collection\s*,\s*legacy_id\s*\)",
        sql,
    )
    assert re.search(
        r"unique\s*\(\s*destination_collection\s*,\s*destination_id\s*\)",
        sql,
    )


def test_provenance_batch_foreign_keys_bind_the_same_source_system():
    sql = _sql().lower()

    assert re.search(
        r"unique\s*\(\s*batch_id\s*,\s*source_system\s*\)",
        sql,
    )
    assert re.search(
        r"foreign\s+key\s*\(\s*first_batch_id\s*,\s*source_system\s*\)\s*"
        r"references\s+bravo_shadow\.migration_batches\s*"
        r"\(\s*batch_id\s*,\s*source_system\s*\)",
        sql,
    )
    assert re.search(
        r"foreign\s+key\s*\(\s*last_verified_batch_id\s*,\s*source_system\s*\)\s*"
        r"references\s+bravo_shadow\.migration_batches\s*"
        r"\(\s*batch_id\s*,\s*source_system\s*\)",
        sql,
    )


def test_batch_approval_is_bound_to_exact_manifest_hash():
    sql = _sql().lower()

    assert "approved_manifest_hash = manifest_hash" in sql
    assert "approved_manifest_hash = manifest_hash" in re.sub(r"\s+", " ", sql)


def test_only_disposable_environments_are_allowed():
    sql = _sql().lower()

    assert "environment in ('local_disposable', 'ci_ephemeral')" in sql
    assert "produção" in sql


def test_rls_is_enabled_and_no_grants_or_policies_are_opened():
    sql = _sql().lower()

    assert "enable row level security" in sql
    assert "revoke all on schema bravo_shadow" in sql
    assert "revoke all on table" in sql
    assert not re.search(r"\bgrant\s+", sql)
    assert not re.search(r"\bcreate\s+policy\s+", sql)


def test_draft_contains_no_data_mutation_or_execution_shortcuts():
    sql = _sql().lower()

    assert "não executar" in sql
    assert not re.search(r"\b(insert\s+into|update\s+bravo_shadow|delete\s+from|truncate\s+)\b", sql)
    assert "create table if not exists bravo_shadow.migration_batches" in sql
    assert "create table if not exists bravo_shadow.migration_source_records" in sql


def test_sql_does_not_claim_to_enforce_the_future_application_gate():
    sql = _sql().lower()

    assert "o futuro importador deverá recusar produção" in sql
    assert "este ddl, isoladamente, não executa essa proteção" in sql
