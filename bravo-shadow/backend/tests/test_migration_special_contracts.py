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



def test_unexpected_field_is_reported_without_exposing_its_value():
    inventory = inspect_source_collections({
        "financeiro": [_record(
            id="001", tipo="Receber", planoContaId="", historico="Taxa",
            valor=10.25, tokenAcesso="SEGREDO-SINTETICO"
        )]
    })
    report = assess_special_contracts(inventory)
    assessment = next(item for item in report.assessments if item.key == "financeiro")

    assert assessment.status == "review_required"
    assert assessment.unexpected_fields == ("tokenAcesso",)
    assert "SEGREDO-SINTETICO" not in repr(report)


def test_boolean_and_null_are_not_accepted_as_numeric_stock_values():
    inventory = inspect_source_collections({
        "estoque": [
            _record(id="p1", item="Papel", quantidade=True),
            _record(id="p2", item="Caneta", quantidade=None),
        ]
    })
    report = assess_special_contracts(inventory)
    assessment = next(item for item in report.assessments if item.key == "estoque")

    assert assessment.status == "review_required"
    assert "quantidade" in assessment.type_mismatches


def test_partially_populated_optional_field_is_reported_for_review():
    inventory = inspect_source_collections({
        "estoque": [
            _record(id="p1", item="Papel", quantidade=5, etiqueta="A-1"),
            _record(id="p2", item="Caneta", quantidade=2),
        ]
    })
    report = assess_special_contracts(inventory)
    assessment = next(item for item in report.assessments if item.key == "estoque")

    assert "etiqueta" in assessment.partially_populated
    assert assessment.status == "review_required"


def test_auxiliary_contract_catalog_covers_confirmed_simple_collections():
    from app.core.migration_special_contracts import AUXILIARY_COLLECTION_CONTRACTS

    assert {item.key for item in AUXILIARY_COLLECTION_CONTRACTS} == {
        "formas_monetarias", "motivos_acerto_estoque", "categorias"
    }


def test_auxiliary_contracts_report_shape_without_claiming_import_readiness():
    from app.core.migration_special_contracts import assess_auxiliary_contracts

    inventory = inspect_source_collections({
        "formas_monetarias": [
            _record(id="fm1", nome="Boleto", multaPct=2.0)
        ],
        "motivos_acerto_estoque": [
            _record(id="me1", nome="Compra")
        ],
        "categorias": [
            _record(id="cat1", nome="Atas")
        ],
    })
    report = assess_auxiliary_contracts(inventory)

    assert len(report.assessments) == 3
    assert all(item.status == "review_required" for item in report.assessments)
    assert all(item.record_count == 1 for item in report.assessments)
    assert "allowlists" in report.unassessed_domains[0]


def test_auxiliary_contracts_flag_unknown_fields_and_duplicate_ids_without_values():
    from app.core.migration_special_contracts import assess_auxiliary_contracts

    inventory = inspect_source_collections({
        "categorias": [
            _record(id="cat1", nome="Atas", segredo="VALOR-SINTETICO"),
            _record(id="cat1", nome="Contratos", segredo="OUTRO-VALOR"),
        ]
    })
    report = assess_auxiliary_contracts(inventory)
    categories = next(item for item in report.assessments if item.key == "categorias")

    assert categories.unexpected_fields == ("segredo",)
    assert "VALOR-SINTETICO" not in repr(report)
    assert "OUTRO-VALOR" not in repr(report)
    assert any("IDs ausentes ou IDs duplicados" in reason for reason in categories.review_reasons)
