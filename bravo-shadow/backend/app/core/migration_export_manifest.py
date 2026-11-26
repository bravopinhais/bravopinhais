"""Auditable, payload-free manifest for an authorized legacy export.

The manifest describes the inventory snapshot; it does not export records,
authenticate the exporter, sign the document, or connect to any data source.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime

from app.core.migration_source_snapshot import SourceSnapshot

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _validate_hash(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{field_name} deve ser SHA-256 hexadecimal minúsculo.")


def _validate_timestamp(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("exported_at deve ser uma data ISO-8601 com fuso horário.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("exported_at deve ser uma data ISO-8601 com fuso horário.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("exported_at deve informar fuso horário.")


@dataclass(frozen=True, slots=True)
class ExportManifest:
    manifest_format_version: int
    schema_version: str
    export_id: str
    source_system: str
    source_baseline: str
    source_software: str | None
    exported_at: str
    record_count: int
    snapshot_hash: str
    previous_manifest_hash: str | None
    manifest_hash: str

    def __post_init__(self) -> None:
        if self.manifest_format_version != 1:
            raise ValueError("manifest_format_version não suportada.")
        for name in ("schema_version", "export_id", "source_system", "source_baseline"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} deve ser texto não vazio.")
        if self.source_software is not None and (
            not isinstance(self.source_software, str) or not self.source_software.strip()
        ):
            raise ValueError("source_software deve ser omitido ou texto não vazio.")
        _validate_timestamp(self.exported_at)
        if isinstance(self.record_count, bool) or not isinstance(self.record_count, int) or self.record_count < 0:
            raise ValueError("record_count deve ser inteiro não negativo.")
        _validate_hash(self.snapshot_hash, "snapshot_hash")
        if self.previous_manifest_hash is not None:
            _validate_hash(self.previous_manifest_hash, "previous_manifest_hash")
        _validate_hash(self.manifest_hash, "manifest_hash")
        if self.manifest_hash != calculate_export_manifest_hash(self):
            raise ValueError("manifest_hash não corresponde ao conteúdo do manifesto.")


def _manifest_content(manifest: ExportManifest) -> dict[str, object]:
    return {
        "manifest_format_version": manifest.manifest_format_version,
        "schema_version": manifest.schema_version,
        "export_id": manifest.export_id,
        "source_system": manifest.source_system,
        "source_baseline": manifest.source_baseline,
        "source_software": manifest.source_software,
        "exported_at": manifest.exported_at,
        "record_count": manifest.record_count,
        "snapshot_hash": manifest.snapshot_hash,
        "previous_manifest_hash": manifest.previous_manifest_hash,
    }


def calculate_export_manifest_hash(manifest: ExportManifest) -> str:
    """Hash the canonical manifest fields, excluding manifest_hash itself."""
    payload = json.dumps(
        _manifest_content(manifest),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_export_manifest(
    snapshot: SourceSnapshot,
    *,
    export_id: str,
    schema_version: str = "1",
    source_software: str | None = None,
    previous_manifest_hash: str | None = None,
) -> ExportManifest:
    """Build an immutable manifest from an already validated source snapshot."""
    if not isinstance(snapshot, SourceSnapshot):
        raise TypeError("snapshot deve ser SourceSnapshot validado.")
    values = {
        "manifest_format_version": 1,
        "schema_version": schema_version,
        "export_id": export_id,
        "source_system": snapshot.source_system,
        "source_baseline": snapshot.source_baseline,
        "source_software": source_software,
        "exported_at": snapshot.exported_at,
        "record_count": len(snapshot.records),
        "snapshot_hash": snapshot.snapshot_hash,
        "previous_manifest_hash": previous_manifest_hash,
    }
    provisional = object.__new__(ExportManifest)
    for name, value in values.items():
        object.__setattr__(provisional, name, value)
    digest = hashlib.sha256(
        json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return ExportManifest(**values, manifest_hash=digest)


def verify_export_manifest(manifest: ExportManifest) -> bool:
    """Return false for a non-manifest or any changed canonical field."""
    if not isinstance(manifest, ExportManifest):
        return False
    try:
        _validate_timestamp(manifest.exported_at)
        _validate_hash(manifest.snapshot_hash, "snapshot_hash")
        _validate_hash(manifest.manifest_hash, "manifest_hash")
        if manifest.previous_manifest_hash is not None:
            _validate_hash(manifest.previous_manifest_hash, "previous_manifest_hash")
        return manifest.manifest_hash == calculate_export_manifest_hash(manifest)
    except (TypeError, ValueError):
        return False
