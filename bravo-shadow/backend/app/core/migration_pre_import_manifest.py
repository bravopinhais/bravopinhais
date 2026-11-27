"""Deterministic, privacy-safe pre-import manifest builder.

The manifest binds source evidence and assessment versions. It never authorizes
writes, performs I/O, or persists anything.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Mapping, Sequence

from app.core.migration_envelope_reader import EnvelopeReadResult
from app.core.migration_source_integrity import SourceIntegrityReport

MANIFEST_VERSION = "1"
CANONICALIZATION_VERSION = "json-sort-keys-utf8-no-whitespace-v1"
DEFAULT_PENDING_GATES = (
    "source_snapshot_field_mapping_unverified",
    "financeiro_decimal_semantics_unresolved",
    "document_codec_unconfirmed",
    "stock_history_reconciliation_pending",
    "condominio_singleton_locator_unconfirmed",
)


@dataclass(frozen=True, slots=True)
class PreImportManifest:
    manifest_version: str
    canonicalization_version: str
    raw_source_sha256: str
    source_byte_length: int
    envelope_format_version: int
    snapshot_hash: str
    source_system: str
    source_branch: str
    source_baseline: str
    exported_at: str
    contract_version: str
    compatibility_mapping_version: str
    special_mapping_version: str
    importer_version: str
    target_schema_version: str
    compatibility_mapping: tuple[tuple[str, str], ...]
    special_mapping: tuple[tuple[str, str], ...]
    integrity_status: str
    integrity_summary: tuple[tuple[str, int | str], ...]
    integrity_issue_codes: tuple[str, ...]
    pending_gates: tuple[str, ...]
    readiness: str
    human_approval_required: bool
    writes_authorized: bool
    canonical_json: str
    manifest_sha256: str


def _required_version(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} deve ser texto não vazio.")
    return value.strip()


def _mapping_items(name: str, value: Mapping[str, str] | None) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    items: list[tuple[str, str]] = []
    for source, target in value.items():
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"{name}: chave de origem inválida.")
        if not isinstance(target, str) or not target.strip():
            raise ValueError(f"{name}: destino inválido.")
        items.append((source, target))
    return tuple(sorted(items))


def build_pre_import_manifest(
    source: EnvelopeReadResult,
    integrity: SourceIntegrityReport,
    *,
    contract_version: str,
    compatibility_mapping_version: str,
    special_mapping_version: str,
    importer_version: str,
    target_schema_version: str,
    compatibility_mapping: Mapping[str, str] | None = None,
    special_mapping: Mapping[str, str] | None = None,
    pending_gates: Sequence[str] = DEFAULT_PENDING_GATES,
) -> PreImportManifest:
    """Bind exact source evidence and report metadata into canonical JSON.

    The raw byte digest is deliberately independent from snapshotHash. The
    manifest excludes all source record values, IDs, personal data and blobs.
    A clear assessment only moves the manifest to awaiting_human_approval.
    """
    if not source.validation.valid:
        raise ValueError("Envelope precisa estar estruturalmente válido.")
    if integrity.inventory != source.source_inventory:
        raise ValueError("Relatório de integridade não corresponde ao inventário deste envelope.")
    versions = {
        "contract_version": _required_version("contract_version", contract_version),
        "compatibility_mapping_version": _required_version(
            "compatibility_mapping_version", compatibility_mapping_version
        ),
        "special_mapping_version": _required_version(
            "special_mapping_version", special_mapping_version
        ),
        "importer_version": _required_version("importer_version", importer_version),
        "target_schema_version": _required_version(
            "target_schema_version", target_schema_version
        ),
    }
    gates: list[str] = []
    for gate in pending_gates:
        if not isinstance(gate, str) or not gate.strip():
            raise ValueError("pending_gates deve conter apenas códigos não vazios.")
        gates.append(gate.strip())
    normalized_gates = tuple(sorted(set(gates)))

    envelope = source.envelope
    summary = asdict(integrity.summary)
    summary_items = tuple(sorted(summary.items()))
    issue_codes = tuple(sorted(set(integrity.issue_codes)))
    readiness = (
        "blocked"
        if integrity.summary.status != "structurally_clear"
        or issue_codes
        or normalized_gates
        else "awaiting_human_approval"
    )
    payload = {
        "manifestVersion": MANIFEST_VERSION,
        "canonicalizationVersion": CANONICALIZATION_VERSION,
        "source": {
            "rawSha256": source.raw_file_sha256,
            "byteLength": source.byte_length,
            "envelopeFormatVersion": source.validation.format_version,
            "snapshotHash": envelope["snapshotHash"],
            "sourceSystem": envelope["sourceSystem"],
            "sourceBranch": envelope["sourceBranch"],
            "sourceBaseline": envelope["sourceBaseline"],
            "exportedAt": envelope["exportedAt"],
        },
        "versions": versions,
        "mappings": {
            "compatibility": [list(item) for item in _mapping_items(
                "compatibility_mapping", compatibility_mapping
            )],
            "special": [list(item) for item in _mapping_items(
                "special_mapping", special_mapping
            )],
        },
        "integrity": {
            "status": integrity.summary.status,
            "summary": summary,
            "issueCodes": list(issue_codes),
        },
        "pendingGates": list(normalized_gates),
        "readiness": readiness,
        "humanApprovalRequired": True,
        "writesAuthorized": False,
    }
    canonical = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return PreImportManifest(
        manifest_version=MANIFEST_VERSION,
        canonicalization_version=CANONICALIZATION_VERSION,
        raw_source_sha256=source.raw_file_sha256,
        source_byte_length=source.byte_length,
        envelope_format_version=source.validation.format_version or 0,
        snapshot_hash=envelope["snapshotHash"],
        source_system=envelope["sourceSystem"],
        source_branch=envelope["sourceBranch"],
        source_baseline=envelope["sourceBaseline"],
        exported_at=envelope["exportedAt"],
        contract_version=versions["contract_version"],
        compatibility_mapping_version=versions["compatibility_mapping_version"],
        special_mapping_version=versions["special_mapping_version"],
        importer_version=versions["importer_version"],
        target_schema_version=versions["target_schema_version"],
        compatibility_mapping=_mapping_items("compatibility_mapping", compatibility_mapping),
        special_mapping=_mapping_items("special_mapping", special_mapping),
        integrity_status=integrity.summary.status,
        integrity_summary=summary_items,
        integrity_issue_codes=issue_codes,
        pending_gates=normalized_gates,
        readiness=readiness,
        human_approval_required=True,
        writes_authorized=False,
        canonical_json=canonical,
        manifest_sha256=digest,
    )
