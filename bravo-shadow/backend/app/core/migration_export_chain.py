"""Read-only verification of a sequence of export manifests.

A chain only provides continuity when the expected prior hash is retained
independently. It does not authenticate the exporter or source system.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.migration_export_manifest import ExportManifest, verify_export_manifest


@dataclass(frozen=True, slots=True)
class ExportChainReport:
    valid: bool
    checked: int
    issues: tuple[str, ...]


def verify_export_chain(
    manifests: tuple[ExportManifest, ...],
    *,
    expected_previous_manifest_hash: str | None = None,
) -> ExportChainReport:
    """Verify manifest integrity and links in chronological order, without I/O."""
    if not isinstance(manifests, tuple):
        raise TypeError("manifests deve ser uma tupla imutável.")
    if any(not isinstance(item, ExportManifest) for item in manifests):
        raise TypeError("manifests contém item de tipo inválido.")
    if expected_previous_manifest_hash is not None and (
        not isinstance(expected_previous_manifest_hash, str)
        or len(expected_previous_manifest_hash) != 64
        or any(char not in "0123456789abcdef" for char in expected_previous_manifest_hash)
    ):
        raise ValueError("expected_previous_manifest_hash deve ser SHA-256 hexadecimal minúsculo.")

    issues: list[str] = []
    seen_export_ids: set[str] = set()
    previous_hash = expected_previous_manifest_hash

    for index, manifest in enumerate(manifests):
        if not verify_export_manifest(manifest):
            issues.append(f"manifest_hash_invalid:{index}")
        if manifest.export_id in seen_export_ids:
            issues.append(f"duplicate_export_id:{index}")
        seen_export_ids.add(manifest.export_id)

        if index == 0 and expected_previous_manifest_hash is None:
            if manifest.previous_manifest_hash is not None:
                issues.append("unanchored_first_manifest")
        elif manifest.previous_manifest_hash != previous_hash:
            issues.append(f"previous_hash_mismatch:{index}")

        previous_hash = manifest.manifest_hash

    return ExportChainReport(
        valid=not issues,
        checked=len(manifests),
        issues=tuple(issues),
    )
