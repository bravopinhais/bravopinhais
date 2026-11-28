from app.core.migration_source_integrity import build_source_integrity_report


def _sample():
    return {
        "categorias": [{"id": "cat-1", "nome": "Geral"}],
        "motivos_acerto": [{"id": "mot-1", "nome": "Compra"}],
        "fornecedores": [{"id": "for-1", "cnpj": "001", "razaoSocial": "Fornecedor"}],
        "empregados": [{"id": "emp-1", "nome": "Pessoa", "cargo": "Zelador"}],
        "moradores": [{"id": "mor-1", "bloco": "A", "apartamento": "01", "nome": "Morador"}],
        "conselheiros": [{"id": "con-1", "nome": "Conselheiro", "cargo": "Fiscal"}],
        "plano_contas": [{"id": "pc-1", "codigo": "001", "nome": "Receita", "tipo": "Receber"}],
        "formas_monetarias": [{"id": "fm-1", "nome": "Pix"}],
        "contas_bancarias": [{"id": "cb-1", "banco": "Banco", "saldo": "10.00"}],
        "financeiro": [{
            "id": "fin-1", "tipo": "Receber", "planoContaId": "pc-1",
            "historico": "Taxa", "valor": 10.0,
        }],
        "documentos": [{
            "id": "doc-1", "pasta": "Geral", "titulo": "Ata",
            "nomeArquivo": "ata.pdf", "arquivoCompactadoGzip": "QUJD",
        }],
        "estoque": [{"id": "prod-1", "item": "Papel", "quantidade": 2}],
        "acertos_estoque": [{
            "id": "mov-1", "data": "27/11/2026", "tipo": "Entrada",
            "produtoId": "prod-1", "quantidade": 2, "motivo": "Compra",
        }],
    }


def test_consolidated_report_combines_inventory_and_all_assessors():
    report = build_source_integrity_report(_sample())
    assert report.summary.collection_count == 13
    assert report.summary.record_count == 13
    assert report.summary.orphan_references == 0
    assert report.summary.unresolved_reference_rules == 0
    assert report.summary.special_contracts_requiring_review == 4
    assert report.summary.unassessed_special_domains == 1
    assert report.summary.status == "review_required"
    assert "special_contract_review_required" in report.issue_codes
    assert "special_domains_unassessed" in report.issue_codes


def test_consolidated_report_counts_duplicate_ids_and_orphans():
    data = _sample()
    data["estoque"].append({"id": "prod-1", "item": "Duplicado", "quantidade": 1})
    data["acertos_estoque"].append({
        "id": "mov-2", "data": "27/11/2026", "tipo": "Saída",
        "produtoId": "missing-product", "quantidade": 1, "motivo": "Ajuste",
    })
    report = build_source_integrity_report(data)
    assert report.summary.duplicate_ids == 1
    assert report.summary.orphan_references == 1
    assert report.summary.collections_with_issues == 1
    assert report.summary.status == "review_required"


def test_consolidated_report_never_echoes_record_values_or_personal_data():
    data = _sample()
    data["moradores"][0]["nome"] = "NOME PRIVADO"
    data["moradores"][0]["cpf"] = "00000000000"
    report = build_source_integrity_report(data)
    rendered = repr(report)
    assert "NOME PRIVADO" not in rendered
    assert "00000000000" not in rendered


def test_unmapped_collections_are_reported_as_integrity_issues():
    data = _sample()
    data["colecao_nao_mapeada"] = [{"id": "extra-1", "campo": "valor"}]
    report = build_source_integrity_report(data)
    assert "colecao_nao_mapeada" in report.compatibility.unmapped_source_collections
    assert "unmapped_source_collections" in report.issue_codes
    assert report.summary.status == "review_required"


def test_empty_and_missing_reference_collections_remain_distinct():
    data = _sample()
    data["estoque"] = []
    del data["plano_contas"]
    report = build_source_integrity_report(data)
    assert "plano_contas" in report.references.missing_collections
    assert report.references.assessments[1].target_records == 0
    assert report.summary.status == "review_required"


def test_explicit_mappings_are_forwarded_to_individual_assessors():
    data = _sample()
    data["titulos"] = data.pop("financeiro")
    report = build_source_integrity_report(
        data,
        compatibility_mapping={"titulos": "financeiro"},
        special_mapping={"financeiro": "titulos"},
    )
    assert "titulos" in report.compatibility.unmapped_source_collections
    assert any(item.source_collection == "titulos" for item in report.special_contracts.assessments)
