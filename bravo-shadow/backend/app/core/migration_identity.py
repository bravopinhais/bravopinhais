"""Pure identity/idempotency decisions for the Bravo migration importer.

This module does not read or write a database. Database uniqueness constraints
and transaction locking remain mandatory in the persistence adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ImportClassification = Literal[
    "ready",
    "already_applied",
    "conflict_changed_source",
    "destination_id_collision",
    "mapping_inconsistent",
]


@dataclass(frozen=True, slots=True)
class SourceIdentity:
    source_system: str
    source_collection: str
    legacy_id: str

    def __post_init__(self) -> None:
        for field_name in ("source_system", "source_collection", "legacy_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} deve ser texto não vazio.")


@dataclass(frozen=True, slots=True)
class ExistingSourceMapping:
    source_record_hash: str
    destination_id: str


@dataclass(frozen=True, slots=True)
class IdentityDecision:
    classification: ImportClassification
    destination_id: str | None
    may_insert: bool


def classify_source_identity(
    *,
    incoming_hash: str,
    existing_mapping: ExistingSourceMapping | None,
    destination_id_exists: bool,
) -> IdentityDecision:
    """Classify an import without performing writes or resolving conflicts."""
    if not isinstance(incoming_hash, str) or not incoming_hash.strip():
        raise ValueError("incoming_hash deve ser texto não vazio.")
    if not isinstance(destination_id_exists, bool):
        raise TypeError("destination_id_exists deve ser booleano.")

    if existing_mapping is not None:
        if not isinstance(existing_mapping, ExistingSourceMapping):
            return IdentityDecision("mapping_inconsistent", None, False)
        if (
            not isinstance(existing_mapping.source_record_hash, str)
            or not existing_mapping.source_record_hash.strip()
        ):
            return IdentityDecision("mapping_inconsistent", None, False)
        if (
            not isinstance(existing_mapping.destination_id, str)
            or not existing_mapping.destination_id.strip()
        ):
            return IdentityDecision("mapping_inconsistent", None, False)
        if existing_mapping.source_record_hash == incoming_hash:
            return IdentityDecision(
                "already_applied",
                existing_mapping.destination_id,
                False,
            )
        return IdentityDecision(
            "conflict_changed_source",
            existing_mapping.destination_id,
            False,
        )

    if destination_id_exists:
        return IdentityDecision("destination_id_collision", None, False)

    return IdentityDecision("ready", None, True)
