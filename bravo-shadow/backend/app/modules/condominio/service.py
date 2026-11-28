from typing import Any

from fastapi import HTTPException

from app.core.audit import AuditEvent
from app.core.authorization import AuthenticatedPrincipal
from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import Condominio, CondominioPatch


class CondominioService:
    def __init__(
        self,
        repository: CollectionRepository[dict[str, str], str] | None = None,
        audit_sink: Any | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self.audit_sink = audit_sink

    def get(self) -> Condominio:
        return Condominio(**(self.repository.get("singleton") or {}))

    def update(
        self,
        patch: CondominioPatch,
        *,
        actor: AuthenticatedPrincipal | None = None,
        request_id: str | None = None,
    ) -> Condominio:
        changes = {
            key: value
            for key, value in patch.model_dump(exclude_unset=True).items()
            if value is not None
        }
        if self.audit_sink is not None:
            if not isinstance(actor, AuthenticatedPrincipal) or actor.account_status != "Ativo" or not isinstance(actor.subject, str) or not actor.subject.strip():
                raise HTTPException(status_code=403, detail="Identidade autenticada ativa obrigatória para esta operação.")
            if not isinstance(request_id, str) or not request_id.strip():
                raise HTTPException(status_code=400, detail="Identificador da requisição ausente.")
            method = getattr(self.repository, "replace_audited", None)
            if not callable(method):
                raise HTTPException(status_code=503, detail="Repositório sem contrato de auditoria transacional.")
            if not callable(getattr(self.audit_sink, "append_in_transaction", None)):
                raise HTTPException(status_code=503, detail="Auditoria transacional indisponível.")
            event = AuditEvent(
                actor_subject=actor.subject.strip(),
                action="condominio:update",
                entity_type="condominio",
                entity_id="singleton",
                request_id=request_id.strip(),
            )
            method("singleton", changes, event, self.audit_sink)
        else:
            if hasattr(self.repository, "replace_audited"):
                raise HTTPException(status_code=503, detail="Auditoria persistente não configurada.")
            current = self.repository.get("singleton") or {}
            current.update(changes)
            if self.repository.exists("singleton"):
                self.repository.replace("singleton", current)
            else:
                self.repository.add("singleton", current)
        return self.get()


condominio_service = CondominioService()
