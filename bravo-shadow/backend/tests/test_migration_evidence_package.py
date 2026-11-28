import hashlib
import json

import pytest

from app.core.migration_identity import SourceIdentity
from app.core.migration_plan import DryRunCandidate
from app.core.migration_evidence_package import (
    serialize_evidence_package,
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



def test_serializer_produces_canonical_package_that_round_trips():
    envelope = _package()["sourceEnvelope"]
    identity = SourceIdentity("legacy-bravo", "moradores", "m-1")
    candidate = DryRunCandidate(
        identity=identity,
        source_record_hash=hashlib.sha256(b"record-m1").hexdigest(),
    )
    kwargs = {
        "source_envelope_raw_sha256": hashlib.sha256(b"synthetic-envelope").hexdigest(),
        "manifest_context": {
            "environment": "shadow-test",
            "importerVersion": "1.0.0",
            "mappingVersion": "1.0.0",
            "createdAt": "2026-11-26T15:00:00-03:00",
        },
    }

    first = serialize_evidence_package(envelope, (candidate,), **kwargs)
    second = serialize_evidence_package(envelope, (candidate,), **kwargs)

    assert first == second
    result = read_evidence_package(first)
    assert result.valid is True
    assert result.ready_count == 1


def _rehash(payload):
    payload.pop("packageSha256", None)
    payload["packageSha256"] = hashlib.sha256(json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")).hexdigest()
    return payload


@pytest.mark.parametrize(
    ("mutate", "error_code"),
    [
        (lambda p: p["candidates"][0].update(sourceRecordHash="not-a-hash"),
         "candidate_hash_invalid"),
        (lambda p: p["candidates"][0].update(destinationIdExists=1),
         "destination_id_exists_invalid"),
        (lambda p: p["candidates"][0].update(references={}),
         "references_invalid"),
        (lambda p: p["candidates"][0]["identity"].update(legacyId=7),
         "identity_invalid"),
        (lambda p: p["candidates"][0].update(existingMapping={
            "sourceRecordHash": "b" * 64, "destinationId": " "
        }), "mapping_destination_invalid"),
        (lambda p: p["manifestContext"].update(environment=" "),
         "manifest_context_value_invalid"),
    ],
)
def test_invalid_nested_fields_are_rejected(mutate, error_code):
    payload = _package()
    mutate(payload)
    _rehash(payload)

    with pytest.raises(EvidencePackageError, match=error_code):
        read_evidence_package(_bytes(payload))


def test_candidate_identity_not_in_source_inventory_is_rejected():
    payload = _package()
    payload["candidates"][0]["identity"]["legacyId"] = "unknown-record"
    _rehash(payload)

    with pytest.raises(EvidencePackageError, match="preflight_invalid"):
        read_evidence_package(_bytes(payload))


def test_duplicate_candidate_identity_is_rejected_by_preflight():
    payload = _package()
    payload["candidates"].append(dict(payload["candidates"][0]))
    _rehash(payload)

    with pytest.raises(EvidencePackageError, match="preflight_invalid"):
        read_evidence_package(_bytes(payload))


def test_invalid_utf8_and_non_finite_json_are_rejected():
    with pytest.raises(EvidencePackageError, match="package_invalid_json"):
        read_evidence_package(b"\\xff")

    with pytest.raises(EvidencePackageError, match="json_non_finite_number"):
        read_evidence_package(b'{"value":NaN}')


def test_serializer_rejects_wrong_candidate_container_type():
    with pytest.raises(EvidencePackageError, match="candidate_inventory_invalid"):
        serialize_evidence_package(
            _package()["sourceEnvelope"],
            [],
            source_envelope_raw_sha256=hashlib.sha256(b"x").hexdigest(),
            manifest_context=_package()["manifestContext"],
        )
