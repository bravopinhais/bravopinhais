from app.core.migration_identity import ExistingSourceMapping, SourceIdentity
from app.core.migration_plan import DryRunCandidate, build_dry_run_plan


def source(collection="moradores", legacy_id="001"):
    return SourceIdentity("legacy-bravo", collection, legacy_id)


def test_empty_batch_produces_empty_summary():
    plan = build_dry_run_plan(())

    assert plan.records == ()
    assert plan.summary.total == 0
    assert plan.summary.ready == 0


def test_new_record_is_planned_without_writing():
    plan = build_dry_run_plan((
        DryRunCandidate(source(), "sha256:one"),
    ))

    assert plan.records[0].status == "ready"
    assert plan.records[0].may_insert is True
    assert plan.summary.ready == 1


def test_repeated_source_identity_blocks_all_duplicates():
    candidate = DryRunCandidate(source(), "sha256:one")
    plan = build_dry_run_plan((candidate, candidate))

    assert [record.status for record in plan.records] == [
        "blocked_duplicate_source",
        "blocked_duplicate_source",
    ]
    assert plan.summary.blocked == 2


def test_unresolved_reference_blocks_candidate():
    candidate = DryRunCandidate(
        source(),
        "sha256:one",
        references=(source("categorias", "missing"),),
    )
    plan = build_dry_run_plan((candidate,))

    assert plan.records[0].status == "blocked_unresolved_reference"
    assert plan.records[0].may_insert is False
    assert len(plan.records[0].unresolved_references) == 1


def test_reference_to_batch_record_resolves_by_exact_identity():
    category = source("categorias", "cat-1")
    document = DryRunCandidate(
        source("documentos", "doc-1"),
        "sha256:doc",
        references=(category,),
    )
    category_record = DryRunCandidate(category, "sha256:cat")

    plan = build_dry_run_plan((document, category_record))

    assert plan.records[0].status == "ready"
    assert plan.records[0].unresolved_references == ()


def test_reference_can_resolve_to_explicitly_known_source():
    known = source("categorias", "cat-9")
    candidate = DryRunCandidate(
        source("documentos", "doc-2"),
        "sha256:doc",
        references=(known,),
    )

    plan = build_dry_run_plan(
        (candidate,),
        already_known_sources=frozenset({known}),
    )

    assert plan.records[0].status == "ready"


def test_existing_conflict_is_not_marked_ready_even_if_reference_resolves():
    candidate = DryRunCandidate(
        source(),
        "sha256:new",
        existing_mapping=ExistingSourceMapping("sha256:old", "dest-1"),
    )
    plan = build_dry_run_plan((candidate,))

    assert plan.records[0].status == "conflict_changed_source"
    assert plan.records[0].may_insert is False
    assert plan.summary.conflicts == 1


def test_destination_collision_is_counted_as_conflict():
    candidate = DryRunCandidate(
        source(),
        "sha256:one",
        destination_id_exists=True,
    )
    plan = build_dry_run_plan((candidate,))

    assert plan.records[0].status == "destination_id_collision"
    assert plan.summary.conflicts == 1


def test_plan_order_matches_input_order():
    first = DryRunCandidate(source(legacy_id="1"), "sha256:1")
    second = DryRunCandidate(source(legacy_id="2"), "sha256:2")

    plan = build_dry_run_plan((first, second))

    assert [record.identity.legacy_id for record in plan.records] == ["1", "2"]
