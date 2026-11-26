from app.core.migration_identity import ExistingSourceMapping, SourceIdentity
from app.core.migration_plan import DryRunCandidate
from app.core.migration_preflight import run_migration_preflight
from app.core.migration_report import build_preflight_report
from app.core.migration_manifest import build_migration_manifest
from app.core.migration_decisions import build_decision_register


def setup_batch():
    envelope = {
        "formatVersion": 1,
        "sourceSystem": "legacy-bravo",
        "sourceBranch": "upgrade/project-hardening",
        "sourceBaseline": "synthetic-decisions",
        "exportedAt": "2026-11-26T12:00:00-03:00",
        "collections": {
            "moradores": [{"id": "m1"}, {"id": "m2"}, {"id": "m3"}, {"id": "m4"}],
        },
        "collectionPresence": {"moradores": True},
        "snapshotHash": "b" * 64,
    }
    candidates = (
        DryRunCandidate(SourceIdentity("legacy-bravo", "moradores", "m1"), "hash-m1"),
        DryRunCandidate(
            SourceIdentity("legacy-bravo", "moradores", "m2"),
            "hash-new",
            existing_mapping=ExistingSourceMapping("hash-old", "resident-m2"),
        ),
        DryRunCandidate(
            SourceIdentity("legacy-bravo", "moradores", "m3"),
            "hash-m3",
            destination_id_exists=True,
        ),
        DryRunCandidate(
            SourceIdentity("legacy-bravo", "moradores", "m4"),
            "hash-m4",
            references=(SourceIdentity("legacy-bravo", "fornecedores", "missing"),),
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
    return envelope, candidates, preflight, manifest


def test_register_lists_conflicts_and_blocks_for_human_review():
    _, _, preflight, manifest = setup_batch()

    register = build_decision_register(manifest, preflight)

    assert register.pending_count == 3
    assert {item.kind for item in register.pending} == {
        "changed_source_conflict",
        "destination_id_collision",
        "unresolved_reference",
    }
    assert all(item.requires_human for item in register.pending)
    assert all(item.automatic_action == "none" for item in register.pending)
    assert register.automatic_resolution_count == 0
    assert register.ready_count == 1


def test_register_is_deterministic_for_same_batch():
    _, _, preflight, manifest = setup_batch()

    first = build_decision_register(manifest, preflight)
    second = build_decision_register(manifest, preflight)

    assert first == second
    assert tuple(item.decision_id for item in first.pending) == tuple(
        item.decision_id for item in second.pending
    )


def test_invalid_preflight_issues_are_added_to_review_queue():
    envelope, candidates, _, manifest = setup_batch()
    envelope["formatVersion"] = 99
    invalid = run_migration_preflight(envelope, candidates)

    register = build_decision_register(manifest, invalid)

    assert register.pending_count >= 1
    assert any(item.kind == "preflight_issue" for item in register.pending)
    assert all(item.automatic_action == "none" for item in register.pending)


def test_ready_and_already_applied_records_are_not_review_items():
    _, _, preflight, manifest = setup_batch()

    register = build_decision_register(manifest, preflight)

    assert all(item.status not in {"ready", "already_applied"} for item in register.pending)
