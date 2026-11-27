from app.core.migration_compatibility import assess_source_compatibility
from app.core.migration_source_inventory import inspect_source_collections


def test_exact_schema_match_is_compatible_and_preserves_leading_zero_ids():
    inventory = inspect_source_collections({
        "fornecedores": [{"id": "0001", "cnpj": "00.000.000/0001-00", "razaoSocial": "Fornecedor"}],
    })

    report = assess_source_compatibility(inventory)
    result = report.assessments[0]

    assert result.status == "compatible"
    assert result.missing_required == ()
    assert result.unexpected_source_fields == ()


def test_missing_required_fields_are_blocking_but_optional_gaps_are_reported():
    inventory = inspect_source_collections({
        "moradores": [{"id": "0001", "nome": "Pessoa"}],
    })

    result = assess_source_compatibility(inventory).assessments[0]

    assert result.status == "review_required"
    assert result.missing_required == ("apartamento", "bloco")
    assert set(result.missing_optional) == {
        "cpf", "email", "petNome", "telefone", "vagaGaragem",
    }


def test_numeric_json_value_for_decimal_requires_review():
    inventory = inspect_source_collections({
        "contas_bancarias": [{"id": "1", "banco": "Banco", "saldo": 123.45}],
    })

    result = assess_source_compatibility(inventory).assessments[0]
    saldo = next(field for field in result.fields if field.name == "saldo")

    assert result.status == "review_required"
    assert saldo.status == "review_conversion"
    assert saldo.expected_type == "decimal"


def test_unexpected_source_fields_are_never_silently_dropped():
    inventory = inspect_source_collections({
        "categorias": [{"id": "1", "nome": "Geral", "legadoExtra": "preservar"}],
    })

    result = assess_source_compatibility(inventory).assessments[0]

    assert result.status == "review_required"
    assert result.unexpected_source_fields == ("legadoExtra",)


def test_explicit_mapping_does_not_guess_source_collection_names():
    inventory = inspect_source_collections({
        "categoriasLegado": [{"id": "1", "nome": "Geral"}],
    })

    report = assess_source_compatibility(
        inventory,
        source_to_target={"categoriasLegado": "categorias"},
    )

    assert report.assessments[0].source_collection == "categoriasLegado"
    assert report.assessments[0].target_collection == "categorias"
    assert report.unmapped_target_collections == tuple(sorted({
        "motivos_acerto", "fornecedores", "empregados", "moradores",
        "conselheiros", "plano_contas", "formas_monetarias", "contas_bancarias",
    }))


def test_required_field_missing_from_some_records_requires_review():
    inventory = inspect_source_collections({
        "fornecedores": [
            {"id": "1", "cnpj": "texto", "razaoSocial": "Fornecedor A"},
            {"id": "2", "cnpj": "texto"},
        ],
    })

    result = assess_source_compatibility(inventory).assessments[0]

    assert result.status == "review_required"
    assert result.partially_populated_required == ("razaoSocial",)


def test_empty_collection_is_not_misreported_as_missing_schema_fields():
    inventory = inspect_source_collections({"categorias": []})

    result = assess_source_compatibility(inventory).assessments[0]

    assert result.status == "empty_source_collection"
    assert result.missing_required == ()
    assert result.fields == ()
