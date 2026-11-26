from app.core.migration_pre_import_validation import PreImportValidationReport
from app.core.migration_readiness_report import build_migration_readiness_report
from app.core.migration_report import PreflightReport


def preflight(valid=True, codes=()):
    return PreflightReport(
        valid=valid,
        collections=(),
        total_envelope_records=0,
        total_candidates=0,
        ready=0,
        already_applied=0,
        blocked=0,
        conflicts=0,
        not_planned=0,
        issue_count=len(codes),
        issue_codes=tuple(codes),
    )


def evidence(ready=True, blockers=()):
    return PreImportValidationReport(
        ready=ready,
        source_system="legacy-bravo",
        export_id="export-synthetic-001",
        snapshot_records=0,
        reconciliation_matched=0,
        blockers=tuple(blockers),
    )


def test_consistent_preflight_and_evidence_produce_ready_report():
    result = build_migration_readiness_report(
        preflight=preflight(),
        evidence=evidence(),
    )

    assert result.ready
    assert result.issues == ()
    assert result.critical_count == 0


def test_integrity_issue_is_critical_and_blocks_readiness():
    result = build_migration_readiness_report(
        preflight=preflight(),
        evidence=evidence(False, ("manifest_hash_invalid",)),
    )

    assert not result.ready
    assert result.critical_count == 1
    assert result.issues[0].severity == "critical"
    assert result.issues[0].category == "integrity"


def test_reconciliation_issue_is_high_severity():
    result = build_migration_readiness_report(
        preflight=preflight(),
        evidence=evidence(False, ("reconciliation:missing_mapping",)),
    )

    assert not result.ready
    assert result.high_count == 1
    assert result.issues[0].severity == "high"


def test_preflight_inventory_issue_is_classified_and_deduplicated():
    result = build_migration_readiness_report(
        preflight=preflight(False, ("candidate_inventory_incomplete",)),
        evidence=evidence(False, ("candidate_inventory_incomplete",)),
    )

    assert not result.ready
    assert len(result.issues) == 1
    assert result.issues[0].category == "inventory"
    assert result.high_count == 1


def test_invalid_preflight_without_details_is_not_silently_accepted():
    result = build_migration_readiness_report(
        preflight=preflight(False),
        evidence=evidence(),
    )

    assert not result.ready
    assert result.issues[0].code == "preflight_invalid_without_detail"
