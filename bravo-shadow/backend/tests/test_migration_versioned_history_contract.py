from pathlib import Path
import re

MIGRATIONS = Path(__file__).resolve().parents[2] / "supabase" / "migrations"
EXPECTED = [
    "20261127000100_bravo_shadow_core.sql",
    "20261127000200_bravo_shadow_audit.sql",
    "20261127000300_bravo_shadow_migration_batches.sql",
    "20261127000400_bravo_shadow_migration_execution.sql",
    "20261127000500_bravo_shadow_migration_review.sql",
    "20261127000600_bravo_shadow_pre_import_approval.sql",
]

def test_versioned_migration_history_has_exact_order_and_unique_versions():
    files = sorted(path.name for path in MIGRATIONS.glob("*.sql"))
    assert files == EXPECTED
    versions = [name.split("_", 1)[0] for name in files]
    assert len(versions) == len(set(versions))

def test_migration_dependencies_are_ordered_before_foreign_key_consumers():
    core = (MIGRATIONS / EXPECTED[0]).read_text()
    batches = (MIGRATIONS / EXPECTED[2]).read_text()
    execution = (MIGRATIONS / EXPECTED[3]).read_text()
    assert core.index("create schema if not exists bravo_shadow") < core.index("create table")
    assert batches.index("create table if not exists bravo_shadow.migration_batches") < batches.index("create table if not exists bravo_shadow.migration_source_records")
    assert execution.index("create table if not exists bravo_shadow.migration_executions") < execution.index("create table if not exists bravo_shadow.migration_apply_approvals")
    assert "REFERENCES bravo_shadow.migration_batches" in execution

def test_functional_baseline_contains_final_stock_shape_without_followup_alter():
    core = (MIGRATIONS / EXPECTED[0]).read_text()
    assert "quantidade numeric(14, 3)" in core
    assert "valor_unitario numeric(14, 2)" in core
    assert "module_settings" in core
    assert "alter column quantidade type" not in core.lower()

def test_sensitive_schemas_remain_unexposed_and_without_runtime_grants():
    for name in EXPECTED:
        sql = (MIGRATIONS / name).read_text().lower()
        assert "grant " not in sql
        assert "from public" in sql or "from public," in sql

def test_apply_environment_is_constrained_and_preimport_never_authorizes_writes():
    execution = (MIGRATIONS / EXPECTED[3]).read_text()
    approval = (MIGRATIONS / EXPECTED[5]).read_text()
    assert "environment = 'local_disposable'" in execution
    assert "writes_authorized = false" in approval
    assert "scope = 'dry_run_only'" in approval
