"""Atomic, opt-in migration apply unit; deliberately not wired to application routes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.core.postgres import (
    CommitOutcomeUnknown as PostgresCommitOutcomeUnknown,
    PostgresUnitOfWork,
)


class MigrationApplyError(RuntimeError):
    """Base class for a rejected or failed migration unit."""


class MigrationApplyBlocked(MigrationApplyError):
    """The source identity cannot be safely applied."""


class CommitOutcomeUnknown(PostgresCommitOutcomeUnknown, MigrationApplyError):
    """Commit raised; caller must reconcile state before any retry."""


@dataclass(frozen=True, slots=True)
class MigrationApplyAuthorization:
    manifest_sha256: str
    plan_sha256: str
    environment: str
    scope: str
    writes_authorized: bool


@dataclass(frozen=True, slots=True)
class MigrationApplyCommand:
    batch_id: str
    execution_id: str
    source_system: str
    source_collection: str
    legacy_id: str
    source_record_sha256: str
    hash_version: str
    target_collection: str
    target_payload: dict[str, Any]
    destination_id: str
    manifest_sha256: str
    plan_sha256: str


@dataclass(frozen=True, slots=True)
class MigrationApplyResult:
    classification: str
    destination_id: str | None
    committed: bool
    writes_authorized: bool


class MigrationApplyStore(Protocol):
    """All methods must use only the connection supplied by the unit of work."""

    def lock_batch(self, connection: Any, batch_id: str, execution_id: str) -> None: ...
    def lock_source_identity(
        self, connection: Any, source_system: str, source_collection: str, legacy_id: str
    ) -> None: ...
    def find_source_link(
        self, connection: Any, source_system: str, source_collection: str, legacy_id: str
    ) -> tuple[str, str] | None:
        """Return (record_sha256, destination_id), or None."""
        ...
    def target_id_exists(self, connection: Any, target_collection: str, destination_id: str) -> bool: ...
    def insert_target(
        self, connection: Any, target_collection: str, destination_id: str, payload: dict[str, Any]
    ) -> None: ...
    def insert_source_link(
        self, connection: Any, command: MigrationApplyCommand
    ) -> None: ...
    def insert_success_event(
        self, connection: Any, command: MigrationApplyCommand, destination_id: str
    ) -> None: ...


def _valid_sha256(value: str) -> bool:
    return (
        isinstance(value, str) and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _validate(
    command: MigrationApplyCommand, authorization: MigrationApplyAuthorization
) -> None:
    if not isinstance(command, MigrationApplyCommand):
        raise TypeError("comando de aplicação inválido.")
    if not isinstance(authorization, MigrationApplyAuthorization):
        raise TypeError("autorização de aplicação inválida.")
    required = (
        command.batch_id, command.execution_id, command.source_system,
        command.source_collection, command.legacy_id, command.hash_version,
        command.target_collection, command.destination_id,
    )
    if any(not isinstance(value, str) or not value.strip() for value in required):
        raise ValueError("identidade, destino e versão são obrigatórios.")
    if not _valid_sha256(command.source_record_sha256):
        raise ValueError("hash do registro de origem inválido.")
    if not _valid_sha256(command.manifest_sha256) or not _valid_sha256(command.plan_sha256):
        raise ValueError("hash do manifesto ou plano inválido.")
    if command.manifest_sha256 != authorization.manifest_sha256:
        raise MigrationApplyBlocked("autorização não corresponde ao manifesto.")
    if command.plan_sha256 != authorization.plan_sha256:
        raise MigrationApplyBlocked("autorização não corresponde ao plano.")
    if (
        authorization.environment != "shadow_local"
        or authorization.scope != "migration_apply"
        or authorization.writes_authorized is not True
    ):
        raise MigrationApplyBlocked("aplicação exige autorização explícita e restrita ao Shadow local.")
    if not isinstance(command.target_payload, dict):
        raise ValueError("payload de destino deve ser objeto.")


def apply_one_record(
    connection_factory: Any,
    store: MigrationApplyStore,
    command: MigrationApplyCommand,
    authorization: MigrationApplyAuthorization,
) -> MigrationApplyResult:
    """Apply one record atomically; this function is not exposed by the app.

    The store is a narrow SQL adapter. Every method receives the same connection.
    Unique constraints remain mandatory for source identity and destination PK.
    """
    _validate(command, authorization)
    if not callable(connection_factory):
        raise TypeError("connection_factory explícita é obrigatória.")
    try:
        with PostgresUnitOfWork(connection_factory) as work:
            connection = work.connection
            if connection is None:
                raise MigrationApplyError("A conexão PostgreSQL não foi aberta.")
            if getattr(connection, "autocommit", False) is not False:
                raise MigrationApplyBlocked("autocommit deve estar desativado.")
            store.lock_batch(connection, command.batch_id, command.execution_id)
            store.lock_source_identity(
                connection, command.source_system, command.source_collection, command.legacy_id
            )
            existing = store.find_source_link(
                connection, command.source_system, command.source_collection, command.legacy_id
            )
            if existing is not None:
                old_hash, old_destination_id = existing
                if old_hash == command.source_record_sha256:
                    return MigrationApplyResult("already_applied", old_destination_id, True, False)
                raise MigrationApplyBlocked("conflict_changed_source: hash de origem divergente.")
            if store.target_id_exists(connection, command.target_collection, command.destination_id):
                raise MigrationApplyBlocked("destination_id_collision: ID já existe sem vínculo de origem.")
            store.insert_target(
                connection, command.target_collection, command.destination_id, command.target_payload
            )
            store.insert_source_link(connection, command)
            store.insert_success_event(connection, command, command.destination_id)
        return MigrationApplyResult("applied", command.destination_id, True, True)
    except PostgresCommitOutcomeUnknown as exc:
        raise CommitOutcomeUnknown(str(exc)) from exc
