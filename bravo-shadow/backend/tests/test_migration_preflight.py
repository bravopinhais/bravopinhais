from app.core.migration_identity import SourceIdentity
from app.core.migration_plan import DryRunCandidate
from app.core.migration_preflight import run_migration_preflight


def envelope():
    return {
        "formatVersion": 1,
        "sourceSystem": "legacy-bravo",
        "sourceBranch": "upgrade/project-hardening",
        "sourceBaseline": "synthetic-baseline-01",
        "exportedAt": "2026-11-26T12:00:00-03:00",
        "collections": {
            "moradores": [{"id": "0001", "nome": "Morador sintético"}],
            "categorias": [],
        },
        "collectionPresence": {"moradores": True, "categorias": True},
        "snapshotHash": "b" * 64,
    }


def candidate(collection="moradores", legacy_id="0001", source_system="legacy-bravo"):
    return DryRunCandidate(
        SourceIdentity(source_system, collection, legacy_id),
        "sha256:synthetic",
    )


def test_valid_envelope_and_complete_candidate_set_produce_plan():
    result = run_migration_preflight(envelope(), (candidate(),))

    assert result.valid is True
    assert result.issues == ()
    assert result.plan is not None
    assert result.plan.summary.ready == 1


def test_invalid_envelope_stops_before_planning():
    value = envelope()
    value["formatVersion"] = 7

    result = run_migration_preflight(value, (candidate(),))

    assert result.valid is False
    assert result.plan is None
    assert "unsupported_format_version" in {issue.code for issue in result.issues}


def test_missing_candidate_for_envelope_record_blocks_preflight():
    result = run_migration_preflight(envelope(), ())

    assert result.valid is False
    assert result.plan is None
    assert "candidate_inventory_incomplete" in {i.code for i in result.issues}


def test_candidate_outside_envelope_inventory_blocks_preflight():
    result = run_migration_preflight(
        envelope(),
        (candidate(), candidate("moradores", "not-in-envelope")),
    )

    assert result.valid is False
    assert result.plan is None
    assert "candidate_not_in_envelope" in {i.code for i in result.issues}


def test_candidate_source_system_must_match_envelope():
    result = run_migration_preflight(
        envelope(),
        (candidate(source_system="another-system"),),
    )

    assert result.valid is False
    assert "candidate_source_system_mismatch" in {i.code for i in result.issues}


def test_duplicate_candidates_block_preflight():
    one = candidate()
    result = run_migration_preflight(envelope(), (one, one))

    assert result.valid is False
    assert "duplicate_candidate_identity" in {i.code for i in result.issues}


def test_absent_collection_cannot_contain_records():
    value = envelope()
    value["collectionPresence"]["moradores"] = False

    result = run_migration_preflight(value, (candidate(),))

    assert result.valid is False
    assert result.plan is None
    assert "absent_collection_has_records" in {i.code for i in result.issues}


def test_existing_source_identity_can_resolve_external_reference():
    value = envelope()
    value["collections"]["documentos"] = [
        {"id": "doc-1", "titulo": "Arquivo sintético"}
    ]
    value["collectionPresence"]["documentos"] = True
    known = SourceIdentity("legacy-bravo", "categorias", "cat-known")
    document = DryRunCandidate(
        SourceIdentity("legacy-bravo", "documentos", "doc-1"),
        "sha256:doc",
        references=(known,),
    )

    result = run_migration_preflight(
        value,
        (candidate(), document),
        already_known_sources=frozenset({known}),
    )

    assert result.valid is True
    assert result.plan is not None
    assert result.plan.records[1].status == "ready"


def test_empty_batch_with_empty_candidate_set_is_valid():
    value = envelope()
    value["collections"] = {"moradores": []}
    value["collectionPresence"] = {"moradores": True}

    result = run_migration_preflight(value, ())

    assert result.valid is True
    assert result.plan is not None
    assert result.plan.summary.total == 0
