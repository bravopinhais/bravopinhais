from dataclasses import replace

from app.core.migration_identity import ExistingSourceMapping, SourceIdentity
from app.core.migration_plan import DryRunCandidate
from app.core.migration_preflight import run_migration_preflight
from app.core.migration_report import build_preflight_report
from app.core.migration_manifest import build_migration_manifest
from app.core.migration_manifest_verifier import verify_manifest_against_batch


def sample():
    envelope = {
        "formatVersion": 1,
        "sourceSystem": "legacy-bravo",
        "sourceBranch": "upgrade/project-hardening",
        "sourceBaseline": "synthetic-verifier",
        "exportedAt": "2026-11-26T12:00:00-03:00",
        "collections": {"moradores": [{"id": "m1"}, {"id": "m2"}]},
        "collectionPresence": {"moradores": True},
        "snapshotHash": "f" * 64,
    }
    candidates = (
        DryRunCandidate(SourceIdentity("legacy-bravo", "moradores", "m1"), "sha256:m1"),
        DryRunCandidate(
            SourceIdentity("legacy-bravo", "moradores", "m2"),
            "sha256:m2",
            existing_mapping=ExistingSourceMapping("sha256:m2", "resident-m2"),
        ),
    )
    preflight = run_migration_preflight(envelope, candidates)
    report = build_preflight_report(envelope, candidates, preflight)
    manifest = build_migration_manifest(
        envelope,
        candidates,
        preflight,
        report,
        environment="shadow-test",
        importer_version="1.0.0",
        mapping_version="1.0.0",
        created_at="2026-11-26T15:00:00-03:00",
    )
    return envelope, candidates, preflight, report, manifest


def test_manifest_matches_original_batch_evidence():
    envelope, candidates, preflight, report, manifest = sample()

    result = verify_manifest_against_batch(manifest, envelope, candidates, preflight, report)

    assert result.valid is True
    assert result.issues == ()


def test_manifest_detects_changed_envelope_snapshot():
    envelope, candidates, preflight, report, manifest = sample()
    changed = dict(envelope)
    changed["snapshotHash"] = "a" * 64

    result = verify_manifest_against_batch(manifest, changed, candidates, preflight, report)

    assert result.valid is False
    assert "manifest_evidence_mismatch" in {issue.code for issue in result.issues}


def test_manifest_detects_report_tampering():
    envelope, candidates, preflight, report, manifest = sample()
    changed_report = replace(report, ready=report.ready + 1)

    result = verify_manifest_against_batch(manifest, envelope, candidates, preflight, changed_report)

    assert result.valid is False
    assert "report_evidence_mismatch" in {issue.code for issue in result.issues}


def test_manifest_detects_candidate_identity_change():
    envelope, candidates, preflight, report, manifest = sample()
    changed_candidates = (
        replace(candidates[0], identity=SourceIdentity("legacy-bravo", "moradores", "different")),
        candidates[1],
    )

    result = verify_manifest_against_batch(manifest, envelope, changed_candidates, preflight, report)

    assert result.valid is False
    assert "manifest_evidence_mismatch" in {issue.code for issue in result.issues}
