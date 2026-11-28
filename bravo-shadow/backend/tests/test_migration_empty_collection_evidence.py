from app.core.migration_empty_collection_evidence import (
    EMPTY_DEFAULT_COLLECTIONS,
    assess_empty_default_collections,
)
from app.core.migration_source_inventory import inspect_source_collections


def test_empty_default_collections_do_not_create_inferred_schemas():
    source = {key: [] for key in EMPTY_DEFAULT_COLLECTIONS}
    results = assess_empty_default_collections(inspect_source_collections(source))
    assert len(results) == 8
    assert all(item.status == "schema_unobserved_empty_default" for item in results)
    assert all(item.record_count == 0 for item in results)
    assert all(item.observed_fields == () for item in results)
    assert all(item.import_allowed is False for item in results)


def test_nonempty_synthetic_records_are_observed_but_never_import_authorized():
    source = {key: [] for key in EMPTY_DEFAULT_COLLECTIONS}
    source["categorias"] = [{"id": "synthetic-1", "nome": "Categoria sintética"}]
    results = {item.legacy_key: item for item in assess_empty_default_collections(
        inspect_source_collections(source)
    )}
    assert results["categorias"].status == "records_present_requires_contract"
    assert results["categorias"].observed_fields == ("id", "nome")
    assert results["categorias"].import_allowed is False
    assert results["moradores"].status == "schema_unobserved_empty_default"


def test_missing_source_key_is_not_mistaken_for_an_empty_array():
    results = assess_empty_default_collections(inspect_source_collections({}))
    assert all(item.status == "source_collection_not_found" for item in results)
    assert all(item.import_allowed is False for item in results)
