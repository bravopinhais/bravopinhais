import hashlib
import json

import pytest

from app.core.migration_envelope_reader import (
    EnvelopeReadError,
    read_envelope_bytes,
)


def valid_envelope():
    return {
        "formatVersion": 1,
        "sourceSystem": "legacy-bravo",
        "sourceBranch": "synthetic-fixture",
        "sourceBaseline": "synthetic-baseline-01",
        "exportedAt": "2026-11-26T12:00:00-03:00",
        "collections": {
            "moradores": [{"id": "0001", "nome": "Registro sintético"}],
            "categorias": [],
        },
        "collectionPresence": {"moradores": True, "categorias": True},
        "snapshotHash": "a" * 64,
    }


def test_reader_accepts_utf8_json_and_returns_frozen_envelope():
    raw = json.dumps(valid_envelope(), ensure_ascii=False).encode("utf-8")

    result = read_envelope_bytes(raw)

    assert result.validation.valid is True
    assert result.byte_length == len(raw)
    assert result.raw_file_sha256 == hashlib.sha256(raw).hexdigest()
    assert result.source_inventory.valid_collection_container is True
    assert [item.name for item in result.source_inventory.collections] == ["categorias", "moradores"]
    moradores = result.source_inventory.collections[1]
    assert moradores.records_total == 1
    assert moradores.records_missing_id == 0
    assert moradores.duplicate_ids == 0
    assert {field.name for field in moradores.fields} == {"id", "nome"}
    assert result.envelope["collections"]["moradores"][0]["id"] == "0001"
    assert isinstance(result.envelope["collections"]["moradores"], tuple)
    with pytest.raises(TypeError):
        result.envelope["sourceSystem"] = "changed"


def test_reader_rejects_duplicate_json_keys():
    raw = b'{"formatVersion":1,"formatVersion":1}'

    with pytest.raises(EnvelopeReadError, match="json_duplicate_key"):
        read_envelope_bytes(raw)


def test_reader_rejects_invalid_utf8():
    with pytest.raises(EnvelopeReadError, match="envelope_not_utf8"):
        read_envelope_bytes(b"\xff\xfe")


def test_reader_rejects_invalid_json():
    with pytest.raises(EnvelopeReadError, match="envelope_invalid_json"):
        read_envelope_bytes(b'{"formatVersion":')


def test_reader_rejects_non_finite_json_numbers():
    raw = b'{"formatVersion":NaN}'

    with pytest.raises(EnvelopeReadError, match="json_non_finite_number"):
        read_envelope_bytes(raw)


def test_reader_rejects_empty_and_oversized_payloads():
    with pytest.raises(EnvelopeReadError, match="envelope_empty"):
        read_envelope_bytes(b"")

    with pytest.raises(EnvelopeReadError, match="envelope_too_large"):
        read_envelope_bytes(b'{"x":1}', max_bytes=2)


def test_reader_rejects_structurally_invalid_envelope_without_echoing_payload():
    value = valid_envelope()
    value["collections"]["moradores"][0]["id"] = 1
    raw = json.dumps(value).encode("utf-8")

    with pytest.raises(EnvelopeReadError, match="envelope_invalid_structure:invalid_legacy_id"):
        read_envelope_bytes(raw)


def test_reader_rejects_non_bytes_and_invalid_size_limit():
    with pytest.raises(TypeError, match="raw deve ser bytes"):
        read_envelope_bytes("{}")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="max_bytes"):
        read_envelope_bytes(b"{}", max_bytes=True)
