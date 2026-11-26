"""Structural validation for versioned Bravo migration batch envelopes.

Validation is pure: it does not open files, access a database, or mutate input.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_TOP_LEVEL = frozenset({
    "formatVersion",
    "sourceSystem",
    "sourceBranch",
    "sourceBaseline",
    "exportedAt",
    "collections",
    "collectionPresence",
    "snapshotHash",
})


@dataclass(frozen=True, slots=True)
class EnvelopeIssue:
    code: str
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class EnvelopeValidation:
    valid: bool
    issues: tuple[EnvelopeIssue, ...]
    format_version: int | None


def validate_batch_envelope(value: Any) -> EnvelopeValidation:
    """Validate the v1 envelope shape without guessing or coercing values."""
    issues: list[EnvelopeIssue] = []

    def add(code: str, path: str, message: str) -> None:
        issues.append(EnvelopeIssue(code, path, message))

    if not isinstance(value, Mapping):
        add("envelope_not_object", "$", "O envelope deve ser um objeto.")
        return EnvelopeValidation(False, tuple(issues), None)

    missing = sorted(_REQUIRED_TOP_LEVEL - set(value.keys()))
    for key in missing:
        add("required_field_missing", key, f"Campo obrigatório ausente: {key}.")

    unknown = sorted(set(value.keys()) - _REQUIRED_TOP_LEVEL)
    for key in unknown:
        add("unknown_field", key, f"Campo não reconhecido no formato v1: {key}.")

    version = value.get("formatVersion")
    if type(version) is not int or version != 1:
        add("unsupported_format_version", "formatVersion", "formatVersion deve ser o inteiro 1.")
        parsed_version = None
    else:
        parsed_version = version

    for field in ("sourceSystem", "sourceBranch", "sourceBaseline", "exportedAt"):
        item = value.get(field)
        if not isinstance(item, str) or not item.strip():
            add("invalid_text_field", field, f"{field} deve ser texto não vazio.")

    collections = value.get("collections")
    presence = value.get("collectionPresence")
    if not isinstance(collections, Mapping):
        add("invalid_collections", "collections", "collections deve ser um objeto.")
        collections = None
    if not isinstance(presence, Mapping):
        add("invalid_collection_presence", "collectionPresence", "collectionPresence deve ser um objeto.")
        presence = None

    if collections is not None and presence is not None:
        if set(collections.keys()) != set(presence.keys()):
            add(
                "collection_inventory_mismatch",
                "collectionPresence",
                "As coleções declaradas e as coleções presentes devem ter as mesmas chaves.",
            )

    if collections is not None:
        for name, records in collections.items():
            path = f"collections.{name}"
            if not isinstance(name, str) or not name.strip():
                add("invalid_collection_name", "collections", "Nome de coleção inválido.")
                continue
            if not isinstance(records, list):
                add("invalid_collection_records", path, "Cada coleção deve ser uma lista.")
                continue
            seen_ids: set[str] = set()
            for index, record in enumerate(records):
                record_path = f"{path}[{index}]"
                if not isinstance(record, Mapping):
                    add("record_not_object", record_path, "Cada registro deve ser um objeto.")
                    continue
                legacy_id = record.get("id")
                if not isinstance(legacy_id, str) or not legacy_id.strip():
                    add("invalid_legacy_id", f"{record_path}.id", "O ID legado deve ser texto não vazio.")
                elif legacy_id in seen_ids:
                    add("duplicate_legacy_id", f"{record_path}.id", "ID legado duplicado na coleção.")
                else:
                    seen_ids.add(legacy_id)

    if presence is not None:
        for name, present in presence.items():
            if not isinstance(name, str) or not name.strip():
                add("invalid_collection_name", "collectionPresence", "Nome de coleção inválido.")
            if type(present) is not bool:
                add(
                    "invalid_presence_flag",
                    f"collectionPresence.{name}",
                    "O indicador de presença deve ser booleano.",
                )

    snapshot_hash = value.get("snapshotHash")
    if not isinstance(snapshot_hash, str) or not _SHA256.fullmatch(snapshot_hash):
        add("invalid_snapshot_hash", "snapshotHash", "snapshotHash deve conter 64 caracteres hexadecimais minúsculos.")

    return EnvelopeValidation(
        valid=not issues,
        issues=tuple(issues),
        format_version=parsed_version,
    )
