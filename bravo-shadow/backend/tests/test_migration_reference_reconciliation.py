from app.core.migration_reference_reconciliation import (
    CONFIRMED_REFERENCE_RULES,
    reconcile_collection_references,
)


def test_confirmed_references_resolve_by_exact_text_id():
    report = reconcile_collection_references({
        "financeiro": [
            {"id": "f1", "planoContaId": "pc-01"},
            {"id": "f2", "planoContaId": ""},
        ],
        "plano_contas": [{"id": "pc-01"}],
        "acertos_estoque": [{"id": "m1", "produtoId": "p-01"}],
        "estoque": [{"id": "p-01"}],
    })
    finance, stock = report.assessments
    assert finance.status == "references_resolved"
    assert finance.references_resolved == 1
    assert finance.blank_optional_references == 1
    assert stock.status == "references_resolved"
    assert stock.references_resolved == 1


def test_orphan_references_are_counted_without_exposing_ids():
    report = reconcile_collection_references({
        "financeiro": [{"id": "f1", "planoContaId": "missing-secret-id"}],
        "plano_contas": [{"id": "pc1"}],
        "acertos_estoque": [{"id": "m1", "produtoId": "p1"}],
        "estoque": [{"id": "p1"}],
    })
    finance = report.assessments[0]
    assert finance.orphan_references == 1
    assert finance.status == "review_required"
    assert "missing-secret-id" not in repr(report)


def test_duplicate_and_missing_target_ids_block_reference_acceptance():
    report = reconcile_collection_references({
        "financeiro": [{"id": "f1", "planoContaId": "pc1"}],
        "plano_contas": [{"id": "pc1"}, {"id": "pc1"}, {}],
        "acertos_estoque": [{"id": "m1", "produtoId": "p1"}],
        "estoque": [{"id": "p1"}],
    })
    finance = report.assessments[0]
    assert finance.duplicate_target_ids == 1
    assert finance.target_records_missing_id == 1
    assert finance.status == "review_required"


def test_required_blank_or_invalid_reference_is_not_silently_ignored():
    report = reconcile_collection_references({
        "financeiro": [{"id": "f1", "planoContaId": None}],
        "plano_contas": [{"id": "pc1"}],
        "acertos_estoque": [
            {"id": "m1", "produtoId": ""},
            {"id": "m2", "produtoId": 123},
            {"id": "m3"},
        ],
        "estoque": [{"id": "p1"}],
    })
    stock = report.assessments[1]
    assert stock.invalid_reference_values == 2
    assert stock.source_records_missing_reference_field == 1
    assert stock.status == "review_required"


def test_missing_and_empty_collections_are_distinguished():
    report = reconcile_collection_references({
        "financeiro": [],
        "plano_contas": [],
        "acertos_estoque": [],
        "estoque": [],
    })
    assert report.missing_collections == ()
    assert all(item.status == "review_required" for item in report.assessments)
    assert all(item.source_records == 0 for item in report.assessments)


def test_absent_collection_is_reported_separately_from_empty_collection():
    report = reconcile_collection_references({
        "financeiro": [],
        "plano_contas": [],
    })
    assert report.missing_collections == ("acertos_estoque", "estoque")
    assert report.assessments[1].target_records is None


def test_non_list_container_is_reported_without_reading_payload():
    report = reconcile_collection_references({
        "financeiro": {"id": "f1"},
        "plano_contas": [],
        "acertos_estoque": [],
        "estoque": [],
    })
    assert report.invalid_collection_containers == ("financeiro",)
    assert report.assessments[0].status == "review_required"


def test_only_confirmed_relationships_are_enabled_by_default():
    assert {rule.key for rule in CONFIRMED_REFERENCE_RULES} == {
        "financeiro_plano_contas",
        "acertos_estoque_produtos",
    }
