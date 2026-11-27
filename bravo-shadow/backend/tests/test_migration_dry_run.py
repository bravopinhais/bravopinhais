"""Synthetic coverage for the read-only migration dry-run planner."""
from dataclasses import replace
import hashlib
import pytest
from app.core.migration_dry_run import ExistingSourceLink, build_migration_dry_run
from app.core.migration_pre_import_approval import ApprovalEvidenceResult
from app.core.migration_pre_import_manifest import PreImportManifest

def manifest():
    return PreImportManifest("1","json-sort-keys-utf8-no-whitespace-v1","a"*64,10,1,"b"*64,"legacy-synthetic","synthetic","c"*40,"2026-01-01T00:00:00+00:00","1","1","1","1","1",(("products","estoque"),),(),"structurally_clear",(),(),(),"awaiting_human_approval",True,False,"{}","d"*64)

def approval():
    return ApprovalEvidenceResult(True,True,False,())

def test_classifies_new_repeat_conflict_and_collision():
    same_hash = hashlib.sha256(b'{"id":"same","name":"same"}').hexdigest()
    links = (ExistingSourceLink("legacy-synthetic","products","same",same_hash),ExistingSourceLink("legacy-synthetic","products","changed","0"*64))
    report = build_migration_dry_run(manifest(),approval(),{"products":[{"id":"new"},{"id":"same","name":"same"},{"id":"changed","name":"new"},{"id":"collision"}]},source_to_target={"products":"estoque"},existing_source_links=links,existing_target_ids={"estoque":["collision"]})
    assert (report.planned_inserts,report.already_applied,report.changed_source_conflicts,report.destination_id_collisions)==(1,1,1,1)
    assert report.writes_authorized is False

def test_plan_is_deterministic():
    args=(manifest(),approval(),{"products":[{"id":"1","name":"x"}]})
    kwargs={"source_to_target":{"products":"estoque"}}
    assert build_migration_dry_run(*args,**kwargs).plan_sha256 == build_migration_dry_run(*args,**kwargs).plan_sha256

def test_rollback_is_only_simulated_and_input_is_unchanged():
    records={"products":[{"id":"1"},{"id":"2"}]}
    before=repr(records)
    report=build_migration_dry_run(manifest(),approval(),records,source_to_target={"products":"estoque"},simulate_failure_after=1)
    assert report.status=="simulated_rollback" and report.simulated_rollback_count==1
    assert repr(records)==before and report.writes_authorized is False

def test_missing_and_duplicate_ids_are_aggregated_without_values():
    report=build_migration_dry_run(manifest(),approval(),{"products":[{"name":"missing"},{"id":"x"},{"id":"x"}]},source_to_target={"products":"estoque"})
    assert report.invalid_records==1 and report.duplicate_source_identities==1
    assert "x" not in repr(report)

def test_invalid_approval_and_ambiguous_mapping_are_rejected():
    with pytest.raises(ValueError):
        build_migration_dry_run(manifest(),replace(approval(),eligible_for_dry_run=False),{"products":[]},source_to_target={"products":"estoque"})
    with pytest.raises(ValueError):
        build_migration_dry_run(manifest(),approval(),{"a":[],"b":[]},source_to_target={"a":"estoque","b":"estoque"})


def test_accepts_immutable_envelope_mappings():
    from types import MappingProxyType
    report = build_migration_dry_run(
        manifest(), approval(),
        MappingProxyType({"products": (MappingProxyType({"id": "1", "name": "x"}),)}),
        source_to_target={"products": "estoque"},
    )
    assert report.planned_inserts == 1

def test_missing_mapped_collection_is_not_silently_empty():
    with pytest.raises(ValueError):
        build_migration_dry_run(manifest(), approval(), {}, source_to_target={"products": "estoque"})

def test_invalid_destination_snapshot_is_rejected():
    with pytest.raises(ValueError):
        build_migration_dry_run(manifest(), approval(), {"products": []}, source_to_target={"products": "estoque"}, existing_target_ids={"estoque": [None]})
