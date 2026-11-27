import pytest

from app.core.migration_identity import (
    ExistingSourceMapping,
    SourceIdentity,
    classify_source_identity,
)


def test_source_identity_keeps_legacy_id_as_opaque_text():
    identity = SourceIdentity("legacy-bravo", "moradores", "000123")

    assert identity.legacy_id == "000123"


@pytest.mark.parametrize(
    "field",
    ["source_system", "source_collection", "legacy_id"],
)
def test_source_identity_rejects_blank_parts(field):
    values = {
        "source_system": "legacy-bravo",
        "source_collection": "moradores",
        "legacy_id": "123",
    }
    values[field] = "   "

    with pytest.raises(ValueError):
        SourceIdentity(**values)


def test_new_identity_without_destination_collision_is_ready():
    decision = classify_source_identity(
        incoming_hash="sha256:abc",
        existing_mapping=None,
        destination_id_exists=False,
    )

    assert decision.classification == "ready"
    assert decision.may_insert is True
    assert decision.destination_id is None


def test_same_hash_is_already_applied_and_never_reinserted():
    decision = classify_source_identity(
        incoming_hash="sha256:abc",
        existing_mapping=ExistingSourceMapping("sha256:abc", "mor_1"),
        destination_id_exists=True,
    )

    assert decision.classification == "already_applied"
    assert decision.destination_id == "mor_1"
    assert decision.may_insert is False


def test_changed_hash_is_conflict_and_never_overwritten():
    decision = classify_source_identity(
        incoming_hash="sha256:new",
        existing_mapping=ExistingSourceMapping("sha256:old", "mor_1"),
        destination_id_exists=True,
    )

    assert decision.classification == "conflict_changed_source"
    assert decision.destination_id == "mor_1"
    assert decision.may_insert is False


def test_destination_id_without_source_mapping_is_collision():
    decision = classify_source_identity(
        incoming_hash="sha256:abc",
        existing_mapping=None,
        destination_id_exists=True,
    )

    assert decision.classification == "destination_id_collision"
    assert decision.may_insert is False


def test_incomplete_existing_mapping_is_inconsistent():
    decision = classify_source_identity(
        incoming_hash="sha256:abc",
        existing_mapping=ExistingSourceMapping("", "mor_1"),
        destination_id_exists=True,
    )

    assert decision.classification == "mapping_inconsistent"
    assert decision.may_insert is False


def test_blank_incoming_hash_is_rejected():
    with pytest.raises(ValueError):
        classify_source_identity(
            incoming_hash=" ",
            existing_mapping=None,
            destination_id_exists=False,
        )


@pytest.mark.parametrize(
    "mapping",
    [
        ExistingSourceMapping(None, "mor_1"),
        ExistingSourceMapping(123, "mor_1"),
        ExistingSourceMapping("sha256:abc", None),
        ExistingSourceMapping("sha256:abc", 123),
    ],
)
def test_malformed_existing_mapping_fails_closed(mapping):
    decision = classify_source_identity(
        incoming_hash="sha256:abc",
        existing_mapping=mapping,
        destination_id_exists=False,
    )
    assert decision.classification == "mapping_inconsistent"
    assert decision.may_insert is False
    assert decision.destination_id is None


@pytest.mark.parametrize("value", ["true", 1, None])
def test_destination_collision_flag_must_be_boolean(value):
    with pytest.raises(TypeError, match="destination_id_exists"):
        classify_source_identity(
            incoming_hash="sha256:abc",
            existing_mapping=None,
            destination_id_exists=value,
        )
