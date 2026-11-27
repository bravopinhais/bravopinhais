"""Privacy-safe structural inventory for source migration collections.

The inventory reports schema shape and aggregate counts only. It never returns
record values, identifiers, or payload fragments and performs no I/O.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class FieldInventory:
    name: str
    records_present: int
    value_types: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class CollectionInventory:
    name: str
    records_total: int
    object_records: int
    invalid_records: int
    records_missing_id: int
    duplicate_ids: int
    fields: tuple[FieldInventory, ...]


@dataclass(frozen=True, slots=True)
class SourceInventory:
    valid_collection_container: bool
    collections: tuple[CollectionInventory, ...]
    issue_codes: tuple[str, ...]


def _value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, Mapping):
        return "object"
    if isinstance(value, (list, tuple)):
        return "array"
    return "other"


def inspect_source_collections(value: Any) -> SourceInventory:
    """Return aggregate structure metrics without exposing source values."""
    if not isinstance(value, Mapping):
        return SourceInventory(False, (), ("collections_not_object",))

    issues: set[str] = set()
    results: list[CollectionInventory] = []

    for collection_name in sorted(value, key=lambda item: str(item)):
        records = value[collection_name]
        if not isinstance(collection_name, str) or not collection_name.strip():
            issues.add("invalid_collection_name")
            continue
        if not isinstance(records, (list, tuple)):
            issues.add("collection_records_not_list")
            results.append(CollectionInventory(
                collection_name, 0, 0, 1, 0, 0, ()
            ))
            continue

        field_presence: Counter[str] = Counter()
        field_types: dict[str, Counter[str]] = {}
        seen_ids: set[str] = set()
        missing_ids = 0
        duplicate_ids = 0
        object_records = 0
        invalid_records = 0

        for record in records:
            if not isinstance(record, Mapping):
                invalid_records += 1
                continue
            object_records += 1
            for field_name, field_value in record.items():
                if not isinstance(field_name, str):
                    issues.add("non_text_field_name")
                    continue
                field_presence[field_name] += 1
                field_types.setdefault(field_name, Counter())[_value_type(field_value)] += 1

            legacy_id = record.get("id")
            if not isinstance(legacy_id, str) or not legacy_id.strip():
                missing_ids += 1
            elif legacy_id in seen_ids:
                duplicate_ids += 1
            else:
                seen_ids.add(legacy_id)

        if invalid_records:
            issues.add("non_object_records")
        if missing_ids:
            issues.add("records_missing_id")
        if duplicate_ids:
            issues.add("duplicate_legacy_ids")

        fields = tuple(
            FieldInventory(
                name=field_name,
                records_present=field_presence[field_name],
                value_types=tuple(sorted(field_types[field_name].items())),
            )
            for field_name in sorted(field_presence)
        )
        results.append(CollectionInventory(
            name=collection_name,
            records_total=len(records),
            object_records=object_records,
            invalid_records=invalid_records,
            records_missing_id=missing_ids,
            duplicate_ids=duplicate_ids,
            fields=fields,
        ))

    return SourceInventory(True, tuple(results), tuple(sorted(issues)))
