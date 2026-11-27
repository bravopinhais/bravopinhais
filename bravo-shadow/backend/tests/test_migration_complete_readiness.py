from app.core.migration_complete_readiness import build_complete_migration_readiness
from app.core.migration_pre_import_validation import PreImportValidationReport
from app.core.migration_report import PreflightReport


def _preflight(valid=True, codes=()):
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


def _evidence(ready=True, blockers=()):
    return PreImportValidationReport(
        ready=ready,
        source_system="synthetic-source",
        export_id="synthetic-export",
        snapshot_records=0,
        reconciliation_matched=0,
        blockers=tuple(blockers),
    )


def test_complete_readiness_combines_integrity_and_domain_review_blockers():
    result = build_complete_migration_readiness(
        {"financeiro": [], "plano_contas": [], "estoque": [],
         "acertos_estoque": [], "documentos": []},
        preflight=_preflight(),
        evidence=_evidence(),
    )

    assert result.status == "review_required"
    assert result.source_integrity is not None
    assert result.integrated_assessment.status == "review_required"
    assert result.blocking_reasons
    assert "specialized_domain_approval_pending" in result.blocking_reasons


def test_complete_readiness_blocks_invalid_batch_evidence():
    result = build_complete_migration_readiness(
        {},
        preflight=_preflight(False, ("candidate_inventory_incomplete",)),
        evidence=_evidence(False, ("manifest_hash_invalid",)),
    )

    assert result.status == "blocked"
    assert "manifest_hash_invalid" in result.blocking_reasons
    assert "candidate_inventory_incomplete" in result.blocking_reasons


def test_non_object_collections_fail_closed_without_source_values():
    result = build_complete_migration_readiness(
        ["not", "a", "mapping"],
        preflight=_preflight(),
        evidence=_evidence(),
    )

    assert result.status == "review_required"
    assert result.source_integrity is None
    assert "collections_not_object" in result.blocking_reasons
    assert "not" not in repr(result)


def test_clear_assessment_is_explicitly_not_import_authorization():
    result = build_complete_migration_readiness(
        {},
        preflight=_preflight(),
        evidence=_evidence(),
    )

    # An empty source is not a completed migration; it still needs review.
    assert result.status == "review_required"
    assert result.status != "import_authorized"
