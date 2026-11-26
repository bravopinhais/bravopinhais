"""Deterministic, immutable manifest for a read-only migration preflight.

The manifest records hashes and source identities, never source payload contents.
It is an in-memory value object: this module performs no I/O or persistence.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from app.core.migration_plan import DryRunCandidate
from app.core.migration_preflight import PreflightResult
from app.core.migration_report import PreflightReport


CANONICALIZATION_VERSION = "json-sortkeys-utf8-v1"
MANIFEST_FORMAT_VERSION = 1


@dataclass(frozen=True, slots=True)
class ManifestRecord:
    source_system: str
    source_collection: str
    legacy_id: str
    source_record_hash: str
    status: str


@dataclass(frozen=True, slots=True)
class MigrationManifest:
    format_version: int
    canonicalization_version: str
    batch_id: str
    manifest_hash: str
    snapshot_hash: str
    source_system: str
    source_branch: str
    source_baseline: str
    exported_at: str
    created_at: str
    environment: str
    importer_version: str
    mapping_version: str
    envelope_format_version: int
    collection_presence: tuple[tuple[str, bool], ...]
    records: tuple[ManifestRecord, ...]
    report_totals: tuple[tuple[str, int], ...]
    issue_codes: tuple[str, ...]


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_migration_manifest(
    envelope: Mapping[str, Any],
    candidates: tuple[DryRunCandidate, ...],
    result: PreflightResult,
    report: PreflightReport,
    *,
    environment: str,
    importer_version: str,
    mapping_version: str,
    created_at: str,
) -> MigrationManifest:
    """Create a deterministic manifest from a completed preflight/report pair.

    Caller-supplied timestamps and version labels are recorded verbatim. The
    function refuses invalid preflights or incomplete candidate plans.
    """
    if not result.valid or result.plan is None or not report.valid:
        raise ValueError("Manifesto exige pré-flight válido e plano disponível.")
    if len(result.plan.records) != len(candidates):
        raise ValueError("Quantidade de resultados difere da quantidade de candidatos.")
    if not isinstance(envelope, Mapping):
        raise ValueError("Envelope deve ser um objeto.")
    for field, value in (
        ("environment", environment),
        ("importer_version", importer_version),
        ("mapping_version", mapping_version),
        ("created_at", created_at),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} deve ser texto não vazio.")

    records = tuple(sorted(
        (
            ManifestRecord(
                source_system=candidate.identity.source_system,
                source_collection=candidate.identity.source_collection,
                legacy_id=candidate.identity.legacy_id,
                source_record_hash=candidate.source_record_hash,
                status=planned.status,
            )
            for candidate, planned in zip(candidates, result.plan.records)
        ),
        key=lambda item: (
            item.source_system,
            item.source_collection,
            item.legacy_id,
        ),
    ))
    presence = tuple(sorted(
        (name, present)
        for name, present in envelope["collectionPresence"].items()
    ))
    totals = tuple(sorted((
        ("total_envelope_records", report.total_envelope_records),
        ("total_candidates", report.total_candidates),
        ("ready", report.ready),
        ("already_applied", report.already_applied),
        ("blocked", report.blocked),
        ("conflicts", report.conflicts),
        ("not_planned", report.not_planned),
        ("issue_count", report.issue_count),
    )))
    issue_codes = tuple(sorted(report.issue_codes))

    identity_payload = {
        "sourceSystem": envelope["sourceSystem"],
        "sourceBaseline": envelope["sourceBaseline"],
        "snapshotHash": envelope["snapshotHash"],
    }
    batch_id = "batch-" + _sha256(_canonical_json(identity_payload))

    payload = {
        "formatVersion": MANIFEST_FORMAT_VERSION,
        "canonicalizationVersion": CANONICALIZATION_VERSION,
        "batchId": batch_id,
        "snapshotHash": envelope["snapshotHash"],
        "sourceSystem": envelope["sourceSystem"],
        "sourceBranch": envelope["sourceBranch"],
        "sourceBaseline": envelope["sourceBaseline"],
        "exportedAt": envelope["exportedAt"],
        "createdAt": created_at,
        "environment": environment,
        "importerVersion": importer_version,
        "mappingVersion": mapping_version,
        "envelopeFormatVersion": result.envelope_validation.format_version,
        "collectionPresence": [[name, present] for name, present in presence],
        "records": [
            {
                "sourceSystem": item.source_system,
                "sourceCollection": item.source_collection,
                "legacyId": item.legacy_id,
                "sourceRecordHash": item.source_record_hash,
                "status": item.status,
            }
            for item in records
        ],
        "reportTotals": [[name, count] for name, count in totals],
        "issueCodes": list(issue_codes),
    }
    manifest_hash = _sha256(_canonical_json(payload))

    return MigrationManifest(
        format_version=MANIFEST_FORMAT_VERSION,
        canonicalization_version=CANONICALIZATION_VERSION,
        batch_id=batch_id,
        manifest_hash=manifest_hash,
        snapshot_hash=envelope["snapshotHash"],
        source_system=envelope["sourceSystem"],
        source_branch=envelope["sourceBranch"],
        source_baseline=envelope["sourceBaseline"],
        exported_at=envelope["exportedAt"],
        created_at=created_at,
        environment=environment,
        importer_version=importer_version,
        mapping_version=mapping_version,
        envelope_format_version=result.envelope_validation.format_version,
        collection_presence=presence,
        records=records,
        report_totals=totals,
        issue_codes=issue_codes,
    )
