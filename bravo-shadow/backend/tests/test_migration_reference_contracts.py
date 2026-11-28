from app.core.migration_source_inventory import inspect_source_collections
from app.core.migration_reference_contracts import assess_reference_contracts


def test_reference_contracts_cover_only_confirmed_legacy_fields():
    inventory = inspect_source_collections({
        "plano_contas": [{"id": "01", "codigo": "1.1", "nome": "Receitas", "tipo": "Receita"}],
        "motivos_acerto_estoque": [{"id": "02", "nome": "Compra"}],
    })
    results = {item.collection: item for item in assess_reference_contracts(inventory)}
    assert results["plano_contas"].missing_required == ()
    assert results["motivos_acerto_estoque"].missing_required == ()
    assert all(item.status == "review_required" for item in results.values())


def test_reference_contract_flags_partial_and_unexpected_fields():
    inventory = inspect_source_collections({
        "plano_contas": [
            {"id": "01", "codigo": "1", "nome": "A", "tipo": "Receita", "extra": "x"},
            {"id": "02", "codigo": "2", "nome": "B"},
        ],
        "motivos_acerto_estoque": [{"id": "03", "nome": "Compra"}],
    })
    results = {item.collection: item for item in assess_reference_contracts(inventory)}
    assert "tipo" in results["plano_contas"].partially_populated
    assert results["plano_contas"].unexpected_fields == ("extra",)
    assert results["plano_contas"].status == "review_required"


def test_reference_contract_rejects_non_string_types_and_does_not_guess_aliases():
    inventory = inspect_source_collections({
        "plano_contas": [{"id": "01", "codigo": 1, "nome": "A", "tipo": "Receita"}],
        "motivos_estoque": [{"id": "03", "nome": "Compra"}],
    })
    results = {item.collection: item for item in assess_reference_contracts(inventory)}
    assert "codigo" in results["plano_contas"].type_mismatches
    assert results["motivos_acerto_estoque"].status == "source_collection_not_found"
