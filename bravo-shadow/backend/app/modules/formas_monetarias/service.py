from uuid import uuid4

from fastapi import HTTPException, status

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from app.core.audit import AuditEvent
from app.core.authorization import AuthenticatedPrincipal
from .schemas import FormaMonetaria, FormaMonetariaInput


class FormasMonetariasService:
    """Regras de formas monetárias independentes do mecanismo de persistência."""

    def __init__(
        self,
        repository: CollectionRepository[FormaMonetaria, str] | None = None,
        audit_sink=None,
    ) -> None:
        self.repository = repository or InMemoryCollectionRepository()
        self.audit_sink = audit_sink
        self._items = getattr(self.repository, "_items", {})

    def list(self) -> list[FormaMonetaria]:
        return self.repository.list()

    def create(self, data: FormaMonetariaInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> FormaMonetaria:
        self._ensure_mutation_audit_ready(actor)
        item = FormaMonetaria(id=f"fm_shadow_{uuid4().hex}", **data.model_dump())
        if actor is not None:
            self._audited("formas_monetarias:create", item.id, actor, request_id, "add_audited", item)
        else:
            self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: FormaMonetariaInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> FormaMonetaria:
        self._ensure_mutation_audit_ready(actor)
        if not self.repository.exists(item_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Forma monetária não encontrada.",
            )
        item = FormaMonetaria(id=item_id, **data.model_dump())
        if actor is not None:
            self._audited("formas_monetarias:update", item_id, actor, request_id, "replace_audited", item, item_id)
        else:
            self.repository.replace(item_id, item)
        return item

    def delete(self, item_id: str, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> None:
        self._ensure_mutation_audit_ready(actor)
        if not self.repository.exists(item_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Forma monetária não encontrada.",
            )
        if actor is not None:
            self._audited("formas_monetarias:delete", item_id, actor, request_id, "delete_audited", item_id)
        else:
            self.repository.delete(item_id)

    def _ensure_mutation_audit_ready(self, actor) -> None:
        if self.audit_sink is not None and actor is None:
            raise HTTPException(status_code=403, detail="Identidade autenticada obrigatória para operações auditadas de formas monetárias.")

    def _audited(self, action, entity_id, actor, request_id, method, *args):
        if not isinstance(actor, AuthenticatedPrincipal) or actor.account_status != "Ativo" or not actor.subject.strip():
            raise HTTPException(status_code=403, detail="Ator administrativo inválido.")
        operation = getattr(self.repository, method, None)
        if not callable(operation) or not callable(getattr(self.audit_sink, "append_in_transaction", None)):
            raise HTTPException(status_code=503, detail="Persistência e auditoria transacional indisponíveis.")
        event = AuditEvent(actor_subject=actor.subject.strip(), action=action, entity_type="formas_monetarias", entity_id=entity_id, request_id=request_id)
        if method == "replace_audited":
            operation(args[0], args[1], event, self.audit_sink)
        elif method == "add_audited":
            operation(args[0], event, self.audit_sink)
        else:
            operation(args[0], event, self.audit_sink)


formas_monetarias_service = FormasMonetariasService()
