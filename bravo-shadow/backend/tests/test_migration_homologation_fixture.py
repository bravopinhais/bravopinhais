import json
from pathlib import Path

from app.core.migration_integrated_preflight import run_integrated_migration_preflight


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "migration_homologation_synthetic.json"
)


def test_versioned_synthetic_fixture_exercises_confirmed_references_safely():
    collections = json.loads(FIXTURE.read_text(encoding="utf-8"))
    result = run_integrated_migration_preflight(collections)

    assert result.status == "review_required"
    assert result.source_inventory.valid_collection_container
    assert all(
        item.orphan_references == 0
        for item in result.references.assessments
    )
    assert "specialized_domain_approval_pending" in result.blocking_reasons
    assert "record_value_contracts_have_issues" in result.blocking_reasons
    rendered = repr(result)
    assert "Lançamento sintético" not in rendered
    assert "est-syn-001" not in rendered
