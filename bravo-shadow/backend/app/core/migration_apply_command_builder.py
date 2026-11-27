"""Build immutable apply commands from an exact, reviewed dry-run plan.

This module performs no I/O and grants no write authorization. Destination IDs
and target payloads must be supplied explicitly by a separately reviewed
mapping; legacy IDs are never silently reused as Bravo destination IDs.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from app.core.migration_dry_run import (
    DRY_RUN_VERSION,
    RECORD_HASH_VERSION,
    DryRunReport,
    RecordDecision,
)
from app.core.migration_pre_import_manifest import PreImportManifest
from app.core.migration_transaction import MigrationApplyCommand

APPLYABLE_CLASSIFICATION = "planned_insert"


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _record_hash(record: Mapping[str, Any]) -> str:
    def normalize(value: Any) -> Any:
        if isinstance(value, Mapping):
            if any(not isinstance(key, str) for key in value):
                raise TypeError("record keys must be strings")
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [normalize(item) for item in value]
        if value is None or isinstance(value, (str, bool, int, float)):
            return value
        raise TypeError("record contains a non-JSON value")

    raw = json.dumps(
        normalize(record),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _identity_fingerprint(source_system: str, source_collection: str, legacy_id: str) -> str:
    return _canonical_hash([source_system, source_collection, legacy_id])


def _expected_plan_hash(report: DryRunReport) -> str:
    return _canonical_hash({
        "version": DRY_RUN_VERSION,
        "manifest": report.manifest_sha256,
        "hashVersion": RECORD_HASH_VERSION,
        "decisions": [
            [
                item.source_collection,
                item.target_collection,
                item.identity_fingerprint,
                item.record_sha256,
                item.classification,
            ]
            for item in report.decisions
        ],
        "rollback": report.simulated_rollback,
        "rollbackCount": report.simulated_rollback_count,
    })


def build_apply_commands(
    manifest: PreImportManifest,
    report: DryRunReport,
    collections: Mapping[str, Any],
    *,
    batch_id: str,
    execution_id: str,
    destination_ids: Mapping[str, str],
    target_payloads: Mapping[str, Mapping[str, Any]],
) -> tuple[MigrationApplyCommand, ...]:
    """Create commands for exactly the ready records in a non-simulated plan.

    Both mapping arguments are keyed by the dry-run identity_fingerprint.
    They must have exactly the same key set as the planned inserts. The
    caller must provide destination IDs and fully mapped Bravo payloads; this
    function never guesses either from legacy data.
    """
    if not isinstance(manifest, PreImportManifest) or not isinstance(report, DryRunReport):
        raise TypeError("manifest and dry-run report are required")
    if not isinstance(collections, Mapping):
        raise TypeError("collections must be a mapping")
    if not isinstance(batch_id, str) or not batch_id.strip():
        raise ValueError("batch_id is required")
    if not isinstance(execution_id, str) or not execution_id.strip():
        raise ValueError("execution_id is required")
    if (
        report.dry_run_version != DRY_RUN_VERSION
        or report.status != "dry_run_complete"
        or report.simulated_rollback
        or report.simulated_rollback_count != 0
    ):
        raise ValueError("dry-run must be complete and not simulate rollback")
    if (
        report.manifest_sha256 != manifest.manifest_sha256
        or report.raw_source_sha256 != manifest.raw_source_sha256
        or report.approval_verified is not True
        or report.writes_authorized is not False
        or manifest.writes_authorized is not False
    ):
        raise ValueError("dry-run evidence does not match the immutable manifest")
    if report.plan_sha256 != _expected_plan_hash(report):
        raise ValueError("dry-run plan hash mismatch")

    records_by_identity: dict[str, tuple[str, str, Mapping[str, Any]]] = {}
    for decision in report.decisions:
        if decision.classification != APPLYABLE_CLASSIFICATION:
            continue
        source_records = collections.get(decision.source_collection)
        if not isinstance(source_records, (list, tuple)):
            raise ValueError("source collection missing from immutable input")
        match = None
        for record in source_records:
            if not isinstance(record, Mapping):
                continue
            legacy_id = record.get("id")
            if not isinstance(legacy_id, str) or not legacy_id:
                continue
            fingerprint = _identity_fingerprint(
                manifest.source_system, decision.source_collection, legacy_id
            )
            if fingerprint == decision.identity_fingerprint:
                if match is not None:
                    raise ValueError("source identity is duplicated in supplied collection")
                match = (legacy_id, record)
        if match is None:
            raise ValueError("planned source record cannot be resolved")
        legacy_id, source_record = match
        if _record_hash(source_record) != decision.record_sha256:
            raise ValueError("source record changed after dry-run")
        if decision.identity_fingerprint in records_by_identity:
            raise ValueError("duplicate planned identity fingerprint")
        records_by_identity[decision.identity_fingerprint] = (
            decision.source_collection,
            legacy_id,
            source_record,
        )

    expected_keys = set(records_by_identity)
    if not isinstance(destination_ids, Mapping) or not isinstance(target_payloads, Mapping):
        raise TypeError("explicit destination ID and payload mappings are required")
    if set(destination_ids) != expected_keys or set(target_payloads) != expected_keys:
        raise ValueError("destination mapping keys must exactly match planned inserts")

    commands: list[MigrationApplyCommand] = []
    for decision in report.decisions:
        if decision.classification != APPLYABLE_CLASSIFICATION:
            continue
        fingerprint = decision.identity_fingerprint
        source_collection, legacy_id, _ = records_by_identity[fingerprint]
        destination_id = destination_ids[fingerprint]
        payload = target_payloads[fingerprint]
        if not isinstance(destination_id, str) or not destination_id.strip():
            raise ValueError("destination ID must be explicit non-empty text")
        if not isinstance(payload, Mapping) or not payload:
            raise ValueError("target payload must be an explicit non-empty mapping")
        payload_copy = dict(payload)
        if "id" in payload_copy and payload_copy["id"] != destination_id:
            raise ValueError("target payload ID differs from explicit destination ID")
        payload_copy["id"] = destination_id
        commands.append(MigrationApplyCommand(
            batch_id=batch_id,
            execution_id=execution_id,
            source_system=manifest.source_system,
            source_collection=source_collection,
            legacy_id=legacy_id,
            source_record_sha256=decision.record_sha256 or "",
            hash_version=RECORD_HASH_VERSION,
            target_collection=decision.target_collection,
            target_payload=payload_copy,
            destination_id=destination_id,
            manifest_sha256=manifest.manifest_sha256,
            plan_sha256=report.plan_sha256,
        ))
    if len(commands) != report.planned_inserts:
        raise ValueError("planned insert count does not match generated command count")
    return tuple(commands)
