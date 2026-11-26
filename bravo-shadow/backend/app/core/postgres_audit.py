"""Adaptador PostgreSQL isolado para persistência append-only de auditoria.

Não é conectado à aplicação nesta etapa. A role usada pela fábrica deve ter
somente INSERT na tabela audit_events; o banco deve impor essa restrição.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.audit import AuditEvent
from app.core.postgres import PostgresUnitOfWork


class PostgresAuditSink:
    """Grava um evento por transação curta; não oferece leitura/edição/exclusão."""

    _INSERT = """
        INSERT INTO bravo_shadow.audit_events (
            event_id, occurred_at, actor_subject, action, entity_type,
            entity_id, outcome, request_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    def __init__(self, connection_factory: Callable[[], Any]) -> None:
        if not callable(connection_factory):
            raise TypeError("connection_factory deve ser chamável.")
        self._uow = PostgresUnitOfWork(connection_factory)

    def append(self, event: AuditEvent) -> None:
        if not isinstance(event, AuditEvent):
            raise TypeError("Somente AuditEvent pode ser registrado.")
        with self._uow as uow:
            connection = uow.connection
            if connection is None:
                raise RuntimeError("A conexão PostgreSQL não foi aberta.")
            cursor = connection.cursor()
            try:
                cursor.execute(
                    self._INSERT,
                    (
                        event.event_id,
                        event.occurred_at,
                        event.actor_subject,
                        event.action,
                        event.entity_type,
                        event.entity_id,
                        event.outcome,
                        event.request_id,
                    ),
                )
            finally:
                cursor.close()
