from app.core.migration_integrated_preflight import run_integrated_migration_preflight

def test_integrated_preflight_combines_reports_and_keeps_domain_approval_blocked():
    snapshot = {
        "financeiro": [{"id":"001", "tipo":"Receber", "planoContaId":"pc1",
                        "historico":"synthetic", "valor":10.25}],
        "plano_contas": [{"id":"pc1", "codigo":"1", "nome":"Receita", "tipo":"Receber"}],
        "estoque": [{"id":"p1", "item":"Papel", "quantidade":5}],
        "acertos_estoque": [{"id":"m1", "data":"27/11/2026", "tipo":"Entrada",
                             "produtoId":"p1", "quantidade":2, "motivo":"Compra"}],
        "documentos": [],
    }
    result = run_integrated_migration_preflight(snapshot)
    assert result.status == "review_required"
    assert result.source_inventory.valid_collection_container
    assert result.value_summary.records_assessed == 3
    assert result.value_summary.records_with_issues == 2
    assert "specialized_domain_approval_pending" in result.blocking_reasons
    assert "record_value_contracts_have_issues" in result.blocking_reasons

def test_integrated_preflight_detects_invalid_container_without_throwing():
    result = run_integrated_migration_preflight(["not", "a", "mapping"])
    assert result.status == "blocked"
    assert "collections_not_object" in result.blocking_reasons

def test_integrated_preflight_reports_reference_orphans_without_source_values():
    snapshot = {
        "financeiro": [{"id":"f1", "tipo":"Receber", "planoContaId":"missing",
                        "historico":"private-synthetic", "valor":1.0}],
        "plano_contas": [{"id":"pc1", "codigo":"1", "nome":"Conta", "tipo":"Receber"}],
        "estoque": [{"id":"p1", "item":"Item", "quantidade":1}],
        "acertos_estoque": [{"id":"m1", "data":"2026-11-27T12:00:00-03:00",
                             "tipo":"Entrada", "produtoId":"p1", "quantidade":1,
                             "motivo":"Teste"}],
    }
    result = run_integrated_migration_preflight(snapshot)
    assert any(item.orphan_references == 1 for item in result.references.assessments)
    assert "private-synthetic" not in repr(result)
    assert "'missing'" not in repr(result)
