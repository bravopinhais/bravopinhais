from app.core.migration_source_inventory import inspect_source_collections
from app.core.migration_special_contracts import (
    CONDOMINIO_SINGLETON_CONTRACT,
    SPECIAL_COLLECTION_CONTRACTS,
    assess_special_contracts,
)


def _record(**values):
    return values


def test_special_contract_catalog_covers_four_high_risk_collections():
    assert {item.key for item in SPECIAL_COLLECTION_CONTRACTS} == {
        "financeiro", "documentos", "estoque", "acertos_estoque"
    }


def test_financeiro_numeric_amount_is_flagged_for_review():
    inventory = inspect_source_collections({
        "financeiro": [_record(
            id="001", tipo="Receber", planoContaId="", historico="Taxa", valor=10.25
        )]
    })
    report = assess_special_contracts(inventory)
    assessment = next(item for item in report.assessments if item.key == "financeiro")
    assert assessment.status == "review_required"
    assert "valor" not in assessment.type_mismatches
    assert any("preservação decimal exata" in reason for reason in assessment.review_reasons)


def test_document_codec_risk_is_explicit_even_when_shape_matches():
    inventory = inspect_source_collections({
        "documentos": [_record(
            id="doc1", pasta="Geral", titulo="Ata", nomeArquivo="ata.pdf",
            arquivoCompactadoGzip="QUJD"
        )]
    })
    report = assess_special_contracts(inventory)
    assessment = next(item for item in report.assessments if item.key == "documentos")
    assert assessment.status == "review_required"
    assert any("Gzip RFC 1952" in reason for reason in assessment.review_reasons)


def test_stock_and_movement_collections_are_assessed_separately():
    inventory = inspect_source_collections({
        "estoque": [_record(id="p1", item="Papel", quantidade=5)],
        "acertos_estoque": [_record(
            id="m1", data="27/11/2026", tipo="Entrada",
            produtoId="p1", quantidade=2, motivo="Compra"
        )],
    })
    report = assess_special_contracts(inventory)
    stock = next(item for item in report.assessments if item.key == "estoque")
    movements = next(item for item in report.assessments if item.key == "acertos_estoque")
    assert stock.record_count == 1
    assert movements.record_count == 1
    assert stock.status == movements.status == "review_required"


def test_unknown_legacy_collection_alias_is_not_guessed():
    inventory = inspect_source_collections({"lancamentos": []})
    report = assess_special_contracts(inventory)
    finance = next(item for item in report.assessments if item.key == "financeiro")
    assert finance.status == "source_collection_not_found"
    assert finance.source_collection == "financeiro"


def test_explicit_collection_mapping_is_respected():
    inventory = inspect_source_collections({
        "titulos_financeiros": [_record(
            id="1", tipo="Pagar", planoContaId="pc1", historico="Água", valor=5
        )]
    })
    report = assess_special_contracts(
        inventory, source_to_target={"financeiro": "titulos_financeiros"}
    )
    finance = next(item for item in report.assessments if item.key == "financeiro")
    assert finance.source_collection == "titulos_financeiros"
    assert finance.record_count == 1


def test_condominio_singleton_is_not_misrepresented_as_collection():
    assert CONDOMINIO_SINGLETON_CONTRACT["source_shape"] == "singleton_object"
    assert CONDOMINIO_SINGLETON_CONTRACT["status"] == "manual_source_locator_required"
