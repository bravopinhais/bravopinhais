"""Synthetic, in-memory tests for dry-run to apply-command preparation.

No database, filesystem, network, or real source records are used.
"""
from dataclasses import replace
import hashlib
import json

import pytest

from app.core.migration_apply_command_builder import (
    _expected_plan_hash,
    _identity_fingerprint,
    _record_hash,
    build_apply_commands,
)
from app.core.migration_dry_run import (
    DRY_RUN_VERSION,
    RECORD_HASH_VERSION,
    DryRunReport,
    RecordDecision,
)
from app.core.migration_pre_import_manifest import PreImportManifest


MANIFEST_HASH = "a" * 64
RAW_HASH = "b" * 64
SOURCE_SYSTEM = "legacy_synthetic"
SOURCE_COLLECTION = "produtos"
TARGET_COLLECTION = "estoque"
SOURCE_RECORD = {"id": "legacy-001", "nome": "Caneta azul", "quantidade": 4}
FINGERPRINT = _identity_fingerprint(SOURCE_SYSTEM, SOURCE_COLLECTION, "legacy-001")
RECORD_HASH = _record_hash(SOURCE_RECORD)


def make_manifest(**changes):
    values = dict(
        manifest_version="1",
        canonicalization_version="json-sort-keys-utf8-no-whitespace-v1",
        raw_source_sha256=RAW_HASH,
        source_byte_length=128,
        envelope_format_version=1,
        snapshot_hash="c" * 64,
        source_system=SOURCE_SYSTEM,
        source_branch="synthetic",
        source_baseline="fixture-v1",
        exported_at="2026-11-27T12:00:00Z",
        contract_version="1",
        compatibility_mapping_version="1",
        special_mapping_version="1",
        importer_version="1",
        target_schema_version="1",
        compatibility_mapping=(),
        special_mapping=(),
        integrity_status="structurally_clear",
        integrity_summary=(),
        integrity_issue_codes=(),
        pending_gates=(),
        readiness="awaiting_human_approval",
        human_approval_required=True,
        writes_authorized=False,
        canonical_json="{}",
        manifest_sha256=MANIFEST_HASH,
    )
    values.update(changes)
    return PreImportManifest(**values)


def make_report(**changes):
    decision = RecordDecision(
        SOURCE_COLLECTION, TARGET_COLLECTION, FINGERPRINT, RECORD_HASH, "planned_insert"
    )
    values = dict(
        dry_run_version=DRY_RUN_VERSION,
        manifest_sha256=MANIFEST_HASH,
        raw_source_sha256=RAW_HASH,
        approval_verified=True,
        writes_authorized=False,
        status="dry_run_complete",
        source_records=1,
        planned_inserts=1,
        already_applied=0,
        changed_source_conflicts=0,
        destination_id_collisions=0,
        invalid_records=0,
        duplicate_source_identities=0,
        simulated_rollback=False,
        simulated_rollback_count=0,
        plan_sha256="0" * 64,
        decisions=(decision,),
        discrepancies=(),
    )
    values.update(changes)
    report = DryRunReport(**values)
    return replace(report, plan_sha256=_expected_plan_hash(report))


def build(**kwargs):
    return build_apply_commands(
        kwargs.pop("manifest", make_manifest()),
        kwargs.pop("report", make_report()),
        kwargs.pop("collections", {SOURCE_COLLECTION: [SOURCE_RECORD]}),
        batch_id="synthetic-batch",
        execution_id="synthetic-execution",
        destination_ids=kwargs.pop("destination_ids", {FINGERPRINT: "bravo-item-001"}),
        target_payloads=kwargs.pop(
            "target_payloads", {FINGERPRINT: {"nome": "Caneta azul", "saldo": 4}}
        ),
        **kwargs,
    )


def test_builds_only_explicitly_mapped_planned_insert():
    commands = build()
    assert len(commands) == 1
    command = commands[0]
    assert command.legacy_id == "legacy-001"
    assert command.destination_id == "bravo-item-001"
    assert command.target_payload == {"nome": "Caneta azul", "saldo": 4, "id": "bravo-item-001"}
    assert command.hash_version == RECORD_HASH_VERSION
    assert command.source_record_sha256 == RECORD_HASH


def test_never_assumes_legacy_id_is_destination_id():
    command = build()[0]
    assert command.destination_id != command.legacy_id


def test_changed_source_after_dry_run_is_rejected():
    changed = {**SOURCE_RECORD, "quantidade": 99}
    with pytest.raises(ValueError, match="changed after dry-run"):
        build(collections={SOURCE_COLLECTION: [changed]})


def test_missing_or_extra_destination_mapping_is_rejected():
    with pytest.raises(ValueError, match="keys must exactly match"):
        build(destination_ids={})
    with pytest.raises(ValueError, match="keys must exactly match"):
        build(destination_ids={FINGERPRINT: "bravo-item-001", "extra": "x"})


def test_payload_id_must_match_explicit_destination():
    with pytest.raises(ValueError, match="differs from explicit"):
        build(target_payloads={FINGERPRINT: {"id": "wrong", "nome": "Caneta"}})


def test_manifest_with_pending_gate_is_rejected():
    manifest = make_manifest(pending_gates=("field_mapping_pending",))
    with pytest.raises(ValueError, match="unresolved pre-import gates"):
        build(manifest=manifest)


def test_report_count_inconsistency_is_rejected():
    report = make_report(source_records=2)
    with pytest.raises(ValueError, match="inconsistencies"):
        build(report=report)


def test_report_with_conflict_is_rejected():
    report = make_report(changed_source_conflicts=1)
    with pytest.raises(ValueError, match="inconsistencies"):
        build(report=report)


def test_tampered_plan_hash_is_rejected():
    report = make_report()
    report = replace(report, plan_sha256="d" * 64)
    with pytest.raises(ValueError, match="plan hash mismatch"):
        build(report=report)


def test_rollback_simulation_is_rejected():
    report = make_report(simulated_rollback=True, simulated_rollback_count=1)
    with pytest.raises(ValueError, match="not simulate rollback"):
        build(report=report)


def test_empty_or_non_json_target_payload_is_rejected():
    with pytest.raises(ValueError, match="non-empty mapping"):
        build(target_payloads={FINGERPRINT: {}})
    with pytest.raises(TypeError):
        build(target_payloads={FINGERPRINT: {"unexpected": object()}})
