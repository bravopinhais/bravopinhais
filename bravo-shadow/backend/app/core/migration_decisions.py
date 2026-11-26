"""Human-review queue for migration conflicts and preflight issues.

This module only identifies items requiring review. It does not resolve,
approve, discard, rewrite, or execute any migration record.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Literal

from app.core.migration_plan import DryRunPlan
from app.core.migration_preflight import PreflightResult
from app.core.migration_manifest import MigrationManifest


DecisionKind = Literal[
    "changed_source_conflict",
    "destination_id_collision",
    "mapping_inconsistent",
    "duplicate_source",
    "unresolved_reference",
    "preflight_issue",
]


@dataclass(frozen=True, slots=True)
class PendingDecision:
    decision_id: str
    kind: DecisionKind
    source_system: str | None
    source_collection: str | None
    legacy_id: str | None
    issue_code: str | None
    status: str
    requires_human: bool
    automatic_action: str


@dataclass(frozen=True, slots=True)
class DecisionRegister:
    batch_id: str
    manifest_hash: str
    pending: tuple[PendingDecision, ...]
    pending_count: int
    ready_count: int
    automatic_resolution_count: int


def _record_identity_key(source_system: str, source_collection: str, legacy_id: str) -> str:
    """Encode identity components injectively; delimiters may occur in source IDs."""
    return json.dumps(
        [source_system, source_collection, legacy_id],
        ensure_ascii=False,
        separators=(",", ":"),
    )


_STATUS_TO_KIND: dict[str, DecisionKind] = {
    "conflict_changed_source": "changed_source_conflict",
    "destination_id_collision": "destination_id_collision",
    "mapping_inconsistent": "mapping_inconsistent",
    "blocked_duplicate_source": "duplicate_source",
    "blocked_unresolved_reference": "unresolved_reference",
}


def build_decision_register(
    manifest: MigrationManifest,
    preflight: PreflightResult,
) -> DecisionRegister:
    """Create stable review items from manifest records and preflight issues."""
    pending: list[PendingDecision] = []

    for record in manifest.records:
        kind = _STATUS_TO_KIND.get(record.status)
        if kind is None:
            continue
        identity = _record_identity_key(
            record.source_system,
            record.source_collection,
            record.legacy_id,
        )
        pending.append(
            PendingDecision(
                decision_id=f"{manifest.batch_id}:record:{identity}:{record.status}",
                kind=kind,
                source_system=record.source_system,
                source_collection=record.source_collection,
                legacy_id=record.legacy_id,
                issue_code=None,
                status=record.status,
                requires_human=True,
                automatic_action="none",
            )
        )

    for index, issue in enumerate(preflight.issues):
        pending.append(
            PendingDecision(
                decision_id=f"{manifest.batch_id}:preflight:{index}:{issue.code}",
                kind="preflight_issue",
                source_system=None,
                source_collection=None,
                legacy_id=None,
                issue_code=issue.code,
                status="preflight_invalid",
                requires_human=True,
                automatic_action="none",
            )
        )

    ordered = tuple(sorted(pending, key=lambda item: item.decision_id))
    return DecisionRegister(
        batch_id=manifest.batch_id,
        manifest_hash=manifest.manifest_hash,
        pending=ordered,
        pending_count=len(ordered),
        ready_count=sum(record.status == "ready" for record in manifest.records),
        automatic_resolution_count=0,
    )
