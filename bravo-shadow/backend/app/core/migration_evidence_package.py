"""Strict, bounded reader for versioned migration evidence packages.

The reader reconstructs every derived result from the source envelope and typed
candidates. It is local, deterministic, and has no filesystem, network, or DB I/O.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from app.core.migration_decision_verifier import verify_decision_register_against_batch
from app.core.migration_decisions import build_decision_register
from app.core.migration_envelope import validate_batch_envelope
from app.core.migration_identity import ExistingSourceMapping, SourceIdentity
from app.core.migration_manifest import build_migration_manifest
from app.core.migration_plan import DryRunCandidate
from app.core.migration_preflight import run_migration_preflight
from app.core.migration_report import build_preflight_report

PACKAGE_TYPE = "bravo-migration-evidence"
PACKAGE_FORMAT_VERSION = 1
MAX_PACKAGE_BYTES = 10 * 1024 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TOP_LEVEL = {
    "packageFormatVersion", "packageType", "sourceEnvelope",
    "sourceEnvelopeRawSha256", "candidates", "alreadyKnownSources",
    "manifestContext", "packageSha256",
}
_CONTEXT_FIELDS = {"environment", "importerVersion", "mappingVersion", "createdAt"}
_IDENTITY_FIELDS = {"sourceSystem", "sourceCollection", "legacyId"}
_CANDIDATE_FIELDS = {
    "identity", "sourceRecordHash", "destinationIdExists",
    "existingMapping", "references",
}


class EvidencePackageError(ValueError):
    """Stable, non-sensitive error raised for invalid evidence packages."""


@dataclass(frozen=True, slots=True)
class EvidencePackageResult:
    valid: bool
    package_sha256: str
    source_envelope_raw_sha256: str
    batch_id: str
    manifest_hash: str
    candidate_count: int
    ready_count: int
    pending_decision_count: int
    issue_codes: tuple[str, ...]


def _duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvidencePackageError("json_duplicate_key")
        result[key] = value
    return result


def _reject_constant(_: str) -> None:
    raise EvidencePackageError("json_non_finite_number")


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise EvidencePackageError("json_not_canonicalizable") from exc


def _exact_keys(value: Any, expected: set[str], code: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise EvidencePackageError(code)


def _sha256(value: Any, code: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise EvidencePackageError(code)
    return value


def _identity(value: Any) -> SourceIdentity:
    _exact_keys(value, _IDENTITY_FIELDS, "identity_fields_invalid")
    try:
        return SourceIdentity(
            source_system=value["sourceSystem"],
            source_collection=value["sourceCollection"],
            legacy_id=value["legacyId"],
        )
    except (TypeError, ValueError) as exc:
        raise EvidencePackageError("identity_invalid") from exc


def _candidate(value: Any) -> DryRunCandidate:
    _exact_keys(value, _CANDIDATE_FIELDS, "candidate_fields_invalid")
    source_hash = _sha256(value["sourceRecordHash"], "candidate_hash_invalid")
    if not isinstance(value["destinationIdExists"], bool):
        raise EvidencePackageError("destination_id_exists_invalid")
    mapping_value = value["existingMapping"]
    mapping = None
    if mapping_value is not None:
        _exact_keys(mapping_value, {"sourceRecordHash", "destinationId"}, "mapping_fields_invalid")
        mapping_hash = _sha256(mapping_value["sourceRecordHash"], "mapping_hash_invalid")
        destination_id = mapping_value["destinationId"]
        if not isinstance(destination_id, str) or not destination_id.strip():
            raise EvidencePackageError("mapping_destination_invalid")
        mapping = ExistingSourceMapping(mapping_hash, destination_id)
    references_value = value["references"]
    if not isinstance(references_value, list):
        raise EvidencePackageError("references_invalid")
    return DryRunCandidate(
        identity=_identity(value["identity"]),
        source_record_hash=source_hash,
        destination_id_exists=value["destinationIdExists"],
        existing_mapping=mapping,
        references=tuple(_identity(item) for item in references_value),
    )


def read_evidence_package(
    raw: bytes, *, max_bytes: int = MAX_PACKAGE_BYTES
) -> EvidencePackageResult:
    """Validate bytes and reconstruct the full evidence chain without I/O."""
    if not isinstance(raw, bytes):
        raise TypeError("raw deve ser bytes.")
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError("max_bytes deve ser inteiro positivo.")
    if not raw:
        raise EvidencePackageError("package_empty")
    if len(raw) > max_bytes:
        raise EvidencePackageError("package_too_large")
    try:
        parsed = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except EvidencePackageError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise EvidencePackageError("package_invalid_json") from exc

    _exact_keys(parsed, _TOP_LEVEL, "package_fields_invalid")
    version = parsed["packageFormatVersion"]
    if isinstance(version, bool) or version != PACKAGE_FORMAT_VERSION:
        raise EvidencePackageError("package_version_unsupported")
    if parsed["packageType"] != PACKAGE_TYPE:
        raise EvidencePackageError("package_type_unsupported")

    claimed_package_hash = _sha256(parsed["packageSha256"], "package_hash_invalid")
    hash_payload = {key: value for key, value in parsed.items() if key != "packageSha256"}
    actual_package_hash = hashlib.sha256(_canonical(hash_payload)).hexdigest()
    if claimed_package_hash != actual_package_hash:
        raise EvidencePackageError("package_hash_mismatch")

    raw_source_hash = _sha256(
        parsed["sourceEnvelopeRawSha256"], "source_envelope_raw_hash_invalid"
    )
    envelope = parsed["sourceEnvelope"]
    envelope_validation = validate_batch_envelope(envelope)
    if not envelope_validation.valid:
        raise EvidencePackageError("source_envelope_invalid")

    candidate_values = parsed["candidates"]
    known_values = parsed["alreadyKnownSources"]
    if not isinstance(candidate_values, list) or not isinstance(known_values, list):
        raise EvidencePackageError("identity_inventory_invalid")
    candidates = tuple(_candidate(item) for item in candidate_values)
    known_list = tuple(_identity(item) for item in known_values)
    if len(set(known_list)) != len(known_list):
        raise EvidencePackageError("known_identity_duplicate")

    context = parsed["manifestContext"]
    _exact_keys(context, _CONTEXT_FIELDS, "manifest_context_invalid")
    for key in _CONTEXT_FIELDS:
        if not isinstance(context[key], str) or not context[key].strip():
            raise EvidencePackageError("manifest_context_value_invalid")

    preflight = run_migration_preflight(
        envelope, candidates, already_known_sources=frozenset(known_list)
    )
    if not preflight.valid or preflight.plan is None:
        raise EvidencePackageError("preflight_invalid")
    report = build_preflight_report(envelope, candidates, preflight)
    manifest = build_migration_manifest(
        envelope, candidates, preflight, report,
        environment=context["environment"],
        importer_version=context["importerVersion"],
        mapping_version=context["mappingVersion"],
        created_at=context["createdAt"],
    )
    register = build_decision_register(manifest, preflight)
    integrity = verify_decision_register_against_batch(
        register, manifest, envelope, candidates, preflight, report
    )
    if not integrity.valid:
        raise EvidencePackageError("evidence_chain_invalid")

    return EvidencePackageResult(
        valid=True,
        package_sha256=actual_package_hash,
        source_envelope_raw_sha256=raw_source_hash,
        batch_id=manifest.batch_id,
        manifest_hash=manifest.manifest_hash,
        candidate_count=len(candidates),
        ready_count=report.ready,
        pending_decision_count=register.pending_count,
        issue_codes=(),
    )
