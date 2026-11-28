import hashlib
import json

import pytest

from app.core.migration_evidence_package import (
    EvidencePackageError,
    read_evidence_package,
)


def _identity(legacy_id):
    return {
        "sourceSystem": "legacy-bravo",
        "sourceCollection": "moradores",
        "legacyId": legacy_id,
    }


def _package():
    envelope = {
        "formatVersion": 1,
        "sourceSystem": "legacy-bravo",
        "sourceBranch": "synthetic",
        "sourceBaseline": "package-test",
        "exportedAt": "2026-11-26T12:00:00-03:00",
        "collections": {"moradores": [{"id": "m-1"}]},
        "collectionPresence": {"moradores": True},
        "snapshotHash": "a" * 64,
    }
    payload = {
        "packageFormatVersion": 1,
        "packageType": "bravo-migration-evidence",
        "sourceEnvelope": envelope,
        # This is a declared source-file digest; the package reader cannot
        # independently prove it without the original source-file bytes.
        "sourceEnvelopeRawSha256": hashlib.sha256(b"synthetic-envelope").hexdigest(),
        "candidates": [{
            "identity": _identity("m-1"),
            "sourceRecordHash": hashlib.sha256(b"record-m1").hexdigest(),
            "destinationIdExists": False,
            "existingMapping": None,
            "references": [],
        }],
        "alreadyKnownSources": [],
        "manifestContext": {
            "environment": "shadow-test",
            "importerVersion": "1.0.0",
            "mappingVersion": "1.0.0",
            "createdAt": "2026-11-26T15:00:00-03:00",
        },
    }
    payload["packageSha256"] = hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()
    return payload


def _bytes(payload):
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def test_valid_package_reconstructs_full_evidence_chain():
    result = read_evidence_package(_bytes(_package()))

    assert result.valid is True
    assert result.candidate_count == 1
    assert result.ready_count == 1
    assert result.pending_decision_count == 0
    assert len(result.manifest_hash) == 64


def test_package_hash_tampering_is_rejected():
    payload = _package()
    payload["manifestContext"]["importerVersion"] = "tampered"

    with pytest.raises(EvidencePackageError, match="package_hash_mismatch"):
        read_evidence_package(_bytes(payload))


def test_unknown_top_level_field_is_rejected_even_with_recomputed_hash():
    payload = _package()
    payload["unexpected"] = True
    payload.pop("packageSha256")
    payload["packageSha256"] = hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()

    with pytest.raises(EvidencePackageError, match="package_fields_invalid"):
        read_evidence_package(_bytes(payload))


def test_duplicate_json_keys_are_rejected():
    raw = b'{"packageFormatVersion":1,"packageFormatVersion":1}'

    with pytest.raises(EvidencePackageError, match="json_duplicate_key"):
        read_evidence_package(raw)


def test_unsupported_version_is_rejected():
    payload = _package()
    payload["packageFormatVersion"] = 2
    payload.pop("packageSha256")
    payload["packageSha256"] = hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()

    with pytest.raises(EvidencePackageError, match="package_version_unsupported"):
        read_evidence_package(_bytes(payload))


def test_duplicate_known_identity_is_rejected():
    payload = _package()
    payload["alreadyKnownSources"] = [_identity("known"), _identity("known")]
    payload.pop("packageSha256")
    payload["packageSha256"] = hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()

    with pytest.raises(EvidencePackageError, match="known_identity_duplicate"):
        read_evidence_package(_bytes(payload))


def test_oversized_package_is_rejected():
    with pytest.raises(EvidencePackageError, match="package_too_large"):
        read_evidence_package(b" " * 20, max_bytes=10)
