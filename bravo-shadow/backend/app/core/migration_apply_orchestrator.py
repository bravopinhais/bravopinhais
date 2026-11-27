"""Explicit orchestration from verified dry-run evidence to atomic batch apply.

No routes, frontend, global connection, or default credentials are used here.
All dependencies and reviewed destination mappings are injected by the caller.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.core.authorization import AuthenticatedPrincipal
from app.core.migration_apply_command_builder import build_apply_commands
from app.core.migration_dry_run import DryRunReport
from app.core.migration_pre_import_manifest import PreImportManifest
from app.core.migration_transaction import (
    MigrationApplyResult,
    PersistedMigrationApplyStore,
    apply_batch_with_persisted_approval,
)


def apply_verified_dry_run(
    *,
    connection_factory: Any,
    store: PersistedMigrationApplyStore,
    principal: AuthenticatedPrincipal,
    manifest: PreImportManifest,
    report: DryRunReport,
    collections: Mapping[str, Any],
    batch_id: str,
    execution_id: str,
    destination_ids: Mapping[str, str],
    target_payloads: Mapping[str, Mapping[str, Any]],
    request_id: str | None = None,
) -> tuple[MigrationApplyResult, ...]:
    """Build and apply one exact dry-run batch under persisted approval.

    The builder revalidates immutable source/plan hashes and reviewed mappings.
    The transaction coordinator then checks persisted batch/execution/approval
    rows, active principal, environment, mode and explicit manifest approval
    before any write. This function does not bypass or synthesize that approval.
    """
    commands = build_apply_commands(
        manifest,
        report,
        collections,
        batch_id=batch_id,
        execution_id=execution_id,
        destination_ids=destination_ids,
        target_payloads=target_payloads,
    )
    if not commands:
        raise ValueError("no planned inserts: refusing an empty apply batch")
    return apply_batch_with_persisted_approval(
        connection_factory,
        store,
        commands,
        principal,
        request_id=request_id,
    )
