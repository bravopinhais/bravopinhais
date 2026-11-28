import hashlib
import json
from dataclasses import replace

from app.core.migration_envelope_reader import read_envelope_bytes
from app.core.migration_pre_import_approval import (
    PreImportApprovalEvidence,
    verify_pre_import_approval,
)
from app.core.migration_pre_import_manifest import build_pre_import_manifest
from app.core.migration_source_integrity import build_source_integrity_report


def _manifest():
    envelope = {
        "formatVersion": 1,
        "sourceSystem": "synthetic",
        "sourceBranch": "fixture",
        "sourceBaseline": "baseline",
        "exportedAt": "2026-11-27T12:00:00-03:00",
        "collections": {"categorias": [{"id": "c-1", "nome": "Geral"}]},
        "collectionPresence": {"categorias": True},
        "snapshotHash": "a" * 64,
    }
    raw = json.dumps(envelope).encode()
    source = read_envelope_bytes(raw)
    integrity = build_source_integrity_report(source.envelope["collections"])
    return build_pre_import_manifest(
        source, integrity,
        contract_version="contract-v1",
        compatibility_mapping_version="compat-v1",
        special_mapping_version="special-v1",
        importer_version="importer-v1",
        target_schema_version="schema-v1",
        pending_gates=(),
    )


def _evidence(manifest, **changes):
    values = {
        "event_id": "approval-event-1",
        "manifest_sha256": manifest.manifest_sha256,
        "raw_source_sha256": manifest.raw_source_sha256,
        "snapshot_hash": manifest.snapshot_hash,
        "decision": "approved_for_dry_run",
        "reviewer_id": "internal-user-42",
        "reviewed_at": "2026-11-27T12:30:00-03:00",
        "rationale": "Revisão documental concluída para dry-run isolado.",
        "sequence_no": 1,
    }
    values.update(changes)
    return PreImportApprovalEvidence(**values)


def test_matching_approval_evidence_cannot_override_source_integrity_blockers():
    manifest = _manifest()
    result = verify_pre_import_approval(manifest, _evidence(manifest))
    assert manifest.readiness == "blocked"
    assert result.valid is False
    assert result.eligible_for_dry_run is False
    assert result.writes_authorized is False
    assert "manifest_not_eligible_for_dry_run" in {item.code for item in result.issues}


def test_blocked_manifest_cannot_be_approved_for_dry_run():
    manifest = replace(_manifest(), readiness="blocked", pending_gates=("gate_pending",))
    result = verify_pre_import_approval(manifest, _evidence(manifest))
    assert result.valid is False
    assert result.eligible_for_dry_run is False
    assert "manifest_not_eligible_for_dry_run" in {item.code for item in result.issues}


def test_rejected_or_change_requested_manifest_never_qualifies():
    manifest = _manifest()
    for decision in ("rejected", "request_changes"):
        result = verify_pre_import_approval(
            manifest, _evidence(manifest, decision=decision)
        )
        assert result.valid is True
        assert result.eligible_for_dry_run is False
        assert result.writes_authorized is False


def test_evidence_must_match_exact_manifest_and_source_hashes():
    manifest = _manifest()
    result = verify_pre_import_approval(
        manifest,
        _evidence(manifest, manifest_sha256="b" * 64, raw_source_sha256="c" * 64),
    )
    codes = {item.code for item in result.issues}
    assert "approval_manifest_hash_mismatch" in codes
    assert "approval_source_hash_mismatch" in codes


def test_evidence_requires_timezone_rationale_reviewer_and_dry_run_scope():
    manifest = _manifest()
    result = verify_pre_import_approval(
        manifest,
        _evidence(
            manifest,
            reviewed_at="2026-11-27T12:30:00",
            rationale=" ",
            reviewer_id=" ",
            scope="apply",
            writes_authorized=True,
        ),
    )
    codes = {item.code for item in result.issues}
    assert "approval_timestamp_timezone_required" in codes
    assert "approval_rationale_required" in codes
    assert "approval_reviewer_required" in codes
    assert "approval_scope_invalid" in codes
    assert "approval_must_not_authorize_writes" in codes


def test_approval_timestamp_must_be_valid():
    manifest = _manifest()
    result = verify_pre_import_approval(
        manifest, _evidence(manifest, reviewed_at="not-a-time")
    )
    assert "approval_timestamp_invalid" in {item.code for item in result.issues}


def test_approval_sequence_must_be_positive_integer_not_boolean():
    manifest = _manifest()
    result = verify_pre_import_approval(manifest, _evidence(manifest, sequence_no=True))
    assert "approval_sequence_invalid" in {item.code for item in result.issues}
