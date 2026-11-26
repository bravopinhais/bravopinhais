"""Contract for an immutable, externally supplied legacy source snapshot.

No concrete legacy connector is defined here. Snapshot integrity is checked
against a canonical representation of source identities and record hashes.
Functional payloads are deliberately excluded.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

from app.core.migration_reconciliation import SourceSnapshotRecord


def calculate_snapshot_hash(
    source_system: str,
    records: tuple[SourceSnapshotRecord, ...],
) -> str:
    """Return SHA-256 of a stable identity/hash inventory representation."""
    canonical_records = sorted(
        (
            item.identity.source_system,
            item.identity.source_collection,
            item.identity.legacy_id,
            item.source_record_hash,
        )
        for item in records
    )
    payload = json.dumps(
        {"source_system": source_system, "records": canonical_records},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    source_system: str
    source_baseline: str
    snapshot_hash: str
    exported_at: str
    records: tuple[SourceSnapshotRecord, ...]

    def __post_init__(self) -> None:
        for field_name in ("source_system", "source_baseline", "exported_at"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} deve ser texto não vazio.")
        if (
            not isinstance(self.snapshot_hash, str)
            or len(self.snapshot_hash) != 64
            or any(char not in "0123456789abcdef" for char in self.snapshot_hash)
        ):
            raise ValueError("snapshot_hash deve ser SHA-256 hexadecimal minúsculo.")
        if not isinstance(self.records, tuple):
            raise TypeError("records deve ser uma tupla imutável.")
        if any(not isinstance(item, SourceSnapshotRecord) for item in self.records):
            raise TypeError("records contém item de tipo inválido.")
        if any(item.identity.source_system != self.source_system for item in self.records):
            raise ValueError("todos os registros devem pertencer ao source_system declarado.")
        expected_hash = calculate_snapshot_hash(self.source_system, self.records)
        if self.snapshot_hash != expected_hash:
            raise ValueError("snapshot_hash não corresponde ao inventário recebido.")

    @staticmethod
    def hash_records(
        source_system: str,
        records: tuple[SourceSnapshotRecord, ...],
    ) -> str:
        """Expose canonical hashing to authorized snapshot exporters."""
        if not isinstance(records, tuple):
            raise TypeError("records deve ser uma tupla imutável.")
        if any(not isinstance(item, SourceSnapshotRecord) for item in records):
            raise TypeError("records contém item de tipo inválido.")
        return calculate_snapshot_hash(source_system, records)


class SourceSnapshotProvider(Protocol):
    """Structural interface for a future, explicitly authorized source reader."""

    def load_snapshot(self) -> SourceSnapshot:
        """Return one immutable, integrity-checked snapshot without mutating source."""
        ...
