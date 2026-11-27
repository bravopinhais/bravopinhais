"""Adaptador PostgreSQL append-only para persistência de auditoria.

É construído pelo composition root no modo postgres e injetado nos serviços
que exigem auditoria. A role da aplicação deve ter somente INSERT na tabela
audit_events; essa restrição precisa ser imposta também pelo próprio banco.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.audit import AuditEvent
from app.core.postgres import PostgresUnitOfWork


class PostgresAuditSink:
    """Grava eventos sem oferecer leitura, edição ou exclusão."""

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

    @staticmethod
    def _validate_event(event: AuditEvent) -> None:
        if not isinstance(event, AuditEvent):
            raise TypeError("Somente AuditEvent pode ser registrado.")

    def append_in_transaction(self, connection: Any, event: AuditEvent) -> None:
        """Insere usando conexão do chamador, sem commit, rollback ou close.

        Permite que o serviço grave auditoria e alteração de negócio na mesma
        transação. O chamador é responsável por confirmar ou reverter ambos.
        """
        self._validate_event(event)
        if connection is None or not callable(getattr(connection, "cursor", None)):
            raise TypeError("connection deve ser uma conexão DB-API válida.")

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
        except BaseException as insert_error:
            # Um erro ao liberar o cursor não pode esconder a falha original
            # do INSERT (ou uma interrupção) que motivou o fechamento.
            try:
                cursor.close()
            except BaseException as close_error:
                add_note = getattr(insert_error, "add_note", None)
                if callable(add_note):
                    add_note(
                        "Falha secundária durante fechamento do cursor: "
                        f"{type(close_error).__name__}."
                    )
            raise
        else:
            # Sem falha no INSERT, erro ao fechar o cursor deve ser propagado
            # para que a transação proprietária possa ser revertida.
            cursor.close()

    def append(self, event: AuditEvent) -> None:
        """Abre uma transação própria; não substitui o uso atômico integrado."""
        self._validate_event(event)
        with self._uow as uow:
            connection = uow.connection
            if connection is None:
                raise RuntimeError("A conexão PostgreSQL não foi aberta.")
            self.append_in_transaction(connection, event)
