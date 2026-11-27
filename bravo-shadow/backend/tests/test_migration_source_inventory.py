from app.core.migration_source_inventory import inspect_source_collections


def test_inventory_reports_counts_and_field_coverage_without_values():
    result = inspect_source_collections({
        "moradores": [
            {"id": "0001", "nome": "Dado pessoal", "bloco": "A"},
            {"id": "0002", "nome": "Outro dado pessoal"},
        ],
        "categorias": [],
    })

    assert result.valid_collection_container is True
    moradores = result.collections[1]
    assert moradores.name == "moradores"
    assert moradores.records_total == 2
    assert moradores.object_records == 2
    assert moradores.records_missing_id == 0
    assert moradores.duplicate_ids == 0
    nome = next(field for field in moradores.fields if field.name == "nome")
    assert nome.records_present == 2
    assert nome.value_types == (("string", 2),)
    assert "Dado pessoal" not in repr(result)


def test_inventory_counts_missing_and_duplicate_ids_without_returning_ids():
    result = inspect_source_collections({
        "itens": [
            {"id": "0001", "valor": 10},
            {"id": "0001", "valor": 20},
            {"nome": "sem identificador"},
            {"id": ""},
        ],
    })

    item = result.collections[0]
    assert item.records_missing_id == 2
    assert item.duplicate_ids == 1
    assert "0001" not in repr(result)
    assert "sem identificador" not in repr(result)


def test_inventory_counts_non_object_records_and_non_list_collection():
    result = inspect_source_collections({
        "a": [{"id": "1"}, None, "texto"],
        "b": {"id": "2"},
    })

    assert result.collections[0].invalid_records == 2
    assert result.collections[1].invalid_records == 1
    assert set(result.issue_codes) == {
        "collection_records_not_list",
        "non_object_records",
    }


def test_inventory_handles_non_object_container():
    result = inspect_source_collections([])

    assert result.valid_collection_container is False
    assert result.collections == ()
    assert result.issue_codes == ("collections_not_object",)


def test_inventory_distinguishes_boolean_from_number_and_tracks_mixed_types():
    result = inspect_source_collections({
        "amostra": [
            {"id": "1", "ativo": True, "quantidade": 1},
            {"id": "2", "ativo": "sim", "quantidade": 2.5},
        ],
    })

    fields = {field.name: field for field in result.collections[0].fields}
    assert fields["ativo"].value_types == (("boolean", 1), ("string", 1))
    assert fields["quantidade"].value_types == (("number", 2),)
