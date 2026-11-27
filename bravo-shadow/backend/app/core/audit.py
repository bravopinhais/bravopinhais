"""Tipos e contrato mínimo de auditoria do Bravo Shadow.

O sink PostgreSQL é injetado pelo composition root quando o backend postgres
é selecionado e usado por operações que exigem auditoria. O modo memory não
configura persistência de auditoria; InMemoryAuditSink serve apenas a testes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Literal, Protocol
from uuid import uuid4


AuditOutcome = Literal["success", "denied", "failure"]


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Evento mínimo, imutável e sem payload de negócio ou dados pessoais."""

    actor_subject: str
    action: str
    entity_type: str
    entity_id: str | None = None
    outcome: AuditOutcome = "success"
    request_id: str | None = None
    event_id: str = field(default_factory=lambda: f"audit_{uuid4().hex}")
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        for name in ("actor_subject", "action", "entity_type"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} deve ser uma string não vazia.")
        for name in ("entity_id", "request_id"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} deve ser omitido ou uma string não vazia.")
        if self.outcome not in ("success", "denied", "failure"):
            raise ValueError("outcome inválido.")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise ValueError("occurred_at deve conter fuso horário.")


class AuditSink(Protocol):
    """Destino append-only para eventos produzidos por serviços confiáveis."""

    def append(self, event: AuditEvent) -> None: ...


class InMemoryAuditSink:
    """Adaptador append-only para testes; não usar como auditoria persistente."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._lock = RLock()

    def append(self, event: AuditEvent) -> None:
        if not isinstance(event, AuditEvent):
            raise TypeError("Somente AuditEvent pode ser registrado.")
        with self._lock:
            self._events.append(event)

    def list_events(self) -> tuple[AuditEvent, ...]:
        """Retorna snapshot imutável; não há operações de editar ou excluir."""
        with self._lock:
            return tuple(self._events)