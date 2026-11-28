from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.audit import AuditEvent
from app.core.authorization import AuthenticatedPrincipal
from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import Conselheiro, ConselheiroInput


class ConselheirosService:
    def __init__(
        self,
        repository: CollectionRepository[Conselheiro, str] | None = None,
        audit_sink: Any | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self.audit_sink = audit_sink

    def list(self) -> list[Conselheiro]:
        return self.repository.list()

    def _event(self, actor: AuthenticatedPrincipal | None, action: str, item_id: str, request_id: str | None) -> AuditEvent:
        if not isinstance(actor, AuthenticatedPrincipal) or actor.account_status != "Ativo" or not isinstance(actor.subject, str) or not actor.subject.strip():
            raise HTTPException(status_code=403, detail="Identidade autenticada ativa obrigatória para esta operação.")
        if not isinstance(request_id, str) or not request_id.strip():
            raise HTTPException(status_code=400, detail="Identificador da requisição ausente.")
        if not callable(getattr(self.audit_sink, "append_in_transaction", None)):
            raise HTTPException(status_code=503, detail="Auditoria transacional indisponível.")
        return AuditEvent(
            actor_subject=actor.subject.strip(),
            action=action,
            entity_type="conselheiro",
            entity_id=item_id,
            request_id=request_id.strip(),
        )

    def _audited_method(self, name: str):
        method = getattr(self.repository, name, None)
        if not callable(method):
            raise HTTPException(status_code=503, detail="Repositório sem contrato de auditoria transacional.")
        return method

    def create(self, data: ConselheiroInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> Conselheiro:
        item = Conselheiro(id=f"cons_shadow_{uuid4().hex}", **data.model_dump())
        if self.audit_sink is not None:
            self._audited_method("add_audited")(
                item.id, item, self._event(actor, "conselheiros:create", item.id, request_id), self.audit_sink
            )
        else:
            if hasattr(self.repository, "add_audited"):
                raise HTTPException(status_code=503, detail="Auditoria persistente não configurada.")
            self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: ConselheiroInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> Conselheiro:
        item = Conselheiro(id=item_id, **data.model_dump())
        if self.audit_sink is not None:
            self._audited_method("replace_audited")(
                item_id, item, self._event(actor, "conselheiros:update", item_id, request_id), self.audit_sink
            )
        else:
            if hasattr(self.repository, "replace_audited"):
                raise HTTPException(status_code=503, detail="Auditoria persistente não configurada.")
            if not self.repository.exists(item_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conselheiro não encontrado.")
            self.repository.replace(item_id, item)
        return item

    def delete(self, item_id: str, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> None:
        if self.audit_sink is not None:
            self._audited_method("delete_audited")(
                item_id, self._event(actor, "conselheiros:delete", item_id, request_id), self.audit_sink
            )
        else:
            if hasattr(self.repository, "delete_audited"):
                raise HTTPException(status_code=503, detail="Auditoria persistente não configurada.")
            if not self.repository.exists(item_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conselheiro não encontrado.")
            self.repository.delete(item_id)


conselheiros_service = ConselheirosService()
