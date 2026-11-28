"""Auditoria padronizada de consultas de leitura."""
from fastapi import HTTPException, Request, status

from app.core.audit import AuditEvent
from app.core.authorization import AuthenticatedPrincipal


def audit_read(
    request: Request,
    service,
    actor: AuthenticatedPrincipal,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
) -> None:
    """Registra metadados mínimos; PostgreSQL nunca lê sem auditoria disponível."""
    sink = getattr(service, "audit_sink", None)
    if sink is None:
        if getattr(request.app.state, "storage_backend", None) == "postgres":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auditoria indisponível. A consulta não foi concluída.",
            )
        # O modo memória é exclusivo de testes/demonstração e não promete
        # histórico durável. O ambiente PostgreSQL exige sink persistente.
        return
    event = AuditEvent(
        actor_subject=actor.subject.strip(),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        outcome="success",
        request_id=getattr(request.state, "request_id", None),
    )
    try:
        sink.append(event)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auditoria indisponível. A consulta não foi concluída.",
        ) from exc
