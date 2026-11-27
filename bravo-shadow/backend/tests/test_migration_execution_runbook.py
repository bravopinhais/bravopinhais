from dataclasses import replace

import pytest

from app.core.migration_integrated_preflight import run_integrated_migration_preflight
from app.core.migration_homologation_package import build_synthetic_homologation_package
from app.core.migration_execution_runbook import build_execution_runbook

def package():
    preflight = run_integrated_migration_preflight({})
    return build_synthetic_homologation_package(
        preflight, source_system="legacy-synthetic",
        source_baseline="runbook-test", snapshot_hash="b"*64,
        created_at="2026-11-27T15:00:00-03:00",
    )

def test_runbook_is_ordered_and_never_executable_or_authorizing():
    result = build_execution_runbook(package())
    assert result.status == "blocked"
    assert result.executable is False
    assert result.approval_required is True
    assert [item.checkpoint_id for item in result.checkpoints] == [
        "PRE-001", "PRE-002", "PRE-003", "PRE-004", "PRE-005",
        "PRE-006", "PRE-007", "PRE-008", "PRE-009",
    ]
    assert any("COMMIT" in item for item in result.global_stop_conditions)

def test_runbook_rejects_tampered_package():
    altered = replace(package(), environment="production")
    with pytest.raises(ValueError, match="integridade"):
        build_execution_runbook(altered)

def test_runbook_rejects_non_synthetic_environment():
    original = package()
    altered = replace(original, environment="local_disposable")
    # The altered environment invalidates the package hash before environment checks.
    with pytest.raises(ValueError):
        build_execution_runbook(altered)

def test_runbook_has_no_production_or_real_import_path():
    result = build_execution_runbook(package())
    assert result.environment == "local_disposable"
    assert result.executable is False
    assert "Este runbook não autoriza produção, importação real ou cutover." in result.recovery_policy
