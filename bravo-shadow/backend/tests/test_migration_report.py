from app.core.migration_identity import ExistingSourceMapping
from app.core.migration_plan import DryRunCandidate
from app.core.migration_preflight import run_migration_preflight
from app.core.migration_report import build_preflight_report


def base_envelope():
    return {
        "formatVersion": 1,
        "sourceSystem": "legacy-bravo",
        "sourceBranch": "upgrade/project-hardening",
        "sourceBaseline": "synthetic-report",
        "exportedAt": "2026-11-26T12:00:00-03:00",
        "collections": {
            "moradores": [{"id": "m1"}, {"id": "m2"}, {"id": "m3"}],
            "categorias": [{"id": "c1"}],
        },
        "collectionPresence": {"moradores": True, "categorias": True},
        "snapshotHash": "c" * 64,
    }


def candidate(collection, legacy_id, *, mapping=None, collision=False):
    from app.core.migration_identity import SourceIdentity

    return DryRunCandidate(
        SourceIdentity("legacy-bravo", collection, legacy_id),
        "sha256:" + legacy_id,
        destination_id_exists=collision,
        existing_mapping=mapping,
    )


def test_report_summarizes_each_collection_and_global_totals():
    envelope = base_envelope()
    candidates = (
        candidate("moradores", "m1"),
        candidate(
            "moradores",
            "m2",
            mapping=ExistingSourceMapping("sha256:m2", "resident-2"),
        ),
        candidate("categorias", "c1", collision=True),
    )
    result = run_migration_preflight(envelope, candidates)

    report = build_preflight_report(envelope, candidates, result)
    moradores = next(row for row in report.collections if row.collection == "moradores")
    categorias = next(row for row in report.collections if row.collection == "categorias")

    assert report.valid is True
    assert moradores.envelope_records == 3
    assert moradores.candidates == 2
    assert moradores.ready == 1
    assert moradores.already_applied == 1
    assert moradores.not_planned == 1
    assert categorias.conflicts == 1
    assert report.total_envelope_records == 4
    assert report.ready == 1
    assert report.already_applied == 1
    assert report.conflicts == 1
    assert report.not_planned == 1


def test_report_exposes_preflight_issues_and_does_not_create_a_plan():
    envelope = base_envelope()
    envelope["formatVersion"] = 9
    candidates = (candidate("moradores", "m1"),)
    result = run_migration_preflight(envelope, candidates)

    report = build_preflight_report(envelope, candidates, result)

    assert report.valid is False
    assert report.issue_count >= 1
    assert "unsupported_format_version" in report.issue_codes
    assert report.ready == 0
    assert report.not_planned == 4


def test_report_handles_empty_batch():
    envelope = base_envelope()
    envelope["collections"] = {"moradores": []}
    envelope["collectionPresence"] = {"moradores": True}
    candidates = ()
    result = run_migration_preflight(envelope, candidates)

    report = build_preflight_report(envelope, candidates, result)

    assert report.total_envelope_records == 0
    assert report.total_candidates == 0
    assert report.collections[0].collection == "moradores"
