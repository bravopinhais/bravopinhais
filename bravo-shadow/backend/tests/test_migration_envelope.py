from app.core.migration_envelope import validate_batch_envelope


def valid_envelope():
    return {
        "formatVersion": 1,
        "sourceSystem": "legacy-bravo",
        "sourceBranch": "upgrade/project-hardening",
        "sourceBaseline": "synthetic-baseline-01",
        "exportedAt": "2026-11-26T12:00:00-03:00",
        "collections": {
            "moradores": [{"id": "0001", "nome": "Registro sintético"}],
            "categorias": [],
        },
        "collectionPresence": {"moradores": True, "categorias": True},
        "snapshotHash": "a" * 64,
    }


def test_valid_envelope_is_accepted_without_coercion():
    result = validate_batch_envelope(valid_envelope())

    assert result.valid is True
    assert result.issues == ()
    assert result.format_version == 1


def test_non_object_envelope_is_rejected():
    result = validate_batch_envelope([])

    assert result.valid is False
    assert result.issues[0].code == "envelope_not_object"


def test_missing_and_unknown_fields_are_reported():
    value = valid_envelope()
    del value["sourceSystem"]
    value["surprise"] = True

    result = validate_batch_envelope(value)
    codes = {issue.code for issue in result.issues}

    assert "required_field_missing" in codes
    assert "unknown_field" in codes


def test_only_integer_version_one_is_supported():
    for version in ("1", 2, True):
        value = valid_envelope()
        value["formatVersion"] = version

        result = validate_batch_envelope(value)

        assert result.valid is False
        assert "unsupported_format_version" in {i.code for i in result.issues}


def test_collection_presence_must_match_collection_inventory():
    value = valid_envelope()
    del value["collectionPresence"]["categorias"]

    result = validate_batch_envelope(value)

    assert "collection_inventory_mismatch" in {i.code for i in result.issues}


def test_duplicate_legacy_ids_are_detected_without_numeric_coercion():
    value = valid_envelope()
    value["collections"]["moradores"] = [
        {"id": "001", "nome": "A"},
        {"id": "001", "nome": "B"},
    ]

    result = validate_batch_envelope(value)

    assert "duplicate_legacy_id" in {i.code for i in result.issues}


def test_ids_with_leading_zeroes_remain_valid_text():
    value = valid_envelope()
    value["collections"]["moradores"] = [{"id": "0001"}]

    result = validate_batch_envelope(value)

    assert result.valid is True


def test_numeric_id_is_rejected_not_converted():
    value = valid_envelope()
    value["collections"]["moradores"] = [{"id": 1}]

    result = validate_batch_envelope(value)

    assert "invalid_legacy_id" in {i.code for i in result.issues}


def test_invalid_snapshot_hash_is_rejected():
    value = valid_envelope()
    value["snapshotHash"] = "not-a-hash"

    result = validate_batch_envelope(value)

    assert "invalid_snapshot_hash" in {i.code for i in result.issues}


def test_each_collection_must_be_a_list_of_objects():
    value = valid_envelope()
    value["collections"]["moradores"] = "not-a-list"

    result = validate_batch_envelope(value)

    assert "invalid_collection_records" in {i.code for i in result.issues}


def test_presence_flags_must_be_booleans():
    value = valid_envelope()
    value["collectionPresence"]["moradores"] = "yes"

    result = validate_batch_envelope(value)

    assert "invalid_presence_flag" in {i.code for i in result.issues}


def test_empty_source_metadata_is_rejected():
    value = valid_envelope()
    value["sourceBranch"] = "   "

    result = validate_batch_envelope(value)

    assert "invalid_text_field" in {i.code for i in result.issues}
