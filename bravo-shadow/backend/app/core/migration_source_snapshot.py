"""Contract for an immutable, externally supplied legacy source snapshot.

This module deliberately defines no concrete legacy connector. A future
provider must be implemented only after the source format and read permissions
are reviewed. The contract carries hashes and identities, not payloads.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.migration_reconciliation import SourceSnapshotRecord


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


class SourceSnapshotProvider(Protocol):
    """Structural interface for a future, explicitly authorized source reader."""

    def load_snapshot(self) -> SourceSnapshot:
        """Return one immutable, integrity-checked snapshot without mutating source."""
        ...
