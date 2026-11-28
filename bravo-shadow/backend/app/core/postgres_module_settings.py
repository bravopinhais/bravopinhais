from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.postgres import PostgresUnitOfWork


class PostgresModuleSettingsRepository:
    _table = "bravo_shadow.module_settings"

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        self._connection_factory = connection_factory

    @staticmethod
    def _close(cursor: Any, primary_error: BaseException | None = None) -> None:
        try:
            cursor.close()
        except BaseException as close_error:
            if primary_error is None:
                raise
            add_note = getattr(primary_error, "add_note", None)
            if callable(add_note):
                add_note(f"Falha secundária ao fechar cursor: {type(close_error).__name__}.")

    def list_states(self) -> dict[str, bool]:
        with PostgresUnitOfWork(self._connection_factory) as uow:
            connection = uow.connection
            if connection is None:
                raise RuntimeError("Conexão PostgreSQL indisponível.")
            cursor = connection.cursor()
            try:
                cursor.execute(f"SELECT module_key, enabled FROM {self._table}")
                rows = cursor.fetchall()
            except BaseException as exc:
                self._close(cursor, exc)
                raise
            else:
                self._close(cursor)
            return {str(row[0]): bool(row[1]) for row in rows}

    def set_state_audited(self, key: str, enabled: bool, *, event: Any, audit_sink: Any) -> None:
        self.set_states_audited({key: enabled}, events=[event], audit_sink=audit_sink)

    def set_states_audited(
        self, changes: dict[str, bool], *, events: list[Any], audit_sink: Any
    ) -> None:
        if not changes or len(changes) != len(events):
            raise ValueError("Cada alteração deve possuir exatamente um evento de auditoria.")
        append = getattr(audit_sink, "append_in_transaction", None)
        if not callable(append):
            raise TypeError("O destino de auditoria transacional é obrigatório.")
        with PostgresUnitOfWork(self._connection_factory) as uow:
            connection = uow.connection
            if connection is None:
                raise RuntimeError("Conexão PostgreSQL indisponível.")
            cursor = connection.cursor()
            try:
                cursor.execute(f"LOCK TABLE {self._table} IN SHARE ROW EXCLUSIVE MODE")
                for (key, enabled), event in zip(changes.items(), events, strict=True):
                    cursor.execute(
                        f"INSERT INTO {self._table} (module_key, enabled, updated_at) "
                        "VALUES (%s, %s, now()) "
                        "ON CONFLICT (module_key) DO UPDATE SET "
                        "enabled = EXCLUDED.enabled, updated_at = now()",
                        (key, enabled),
                    )
                    append(connection, event)
            except BaseException as exc:
                self._close(cursor, exc)
                raise
            else:
                self._close(cursor)
