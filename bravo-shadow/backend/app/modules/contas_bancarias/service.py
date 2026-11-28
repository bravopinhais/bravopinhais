from uuid import uuid4

from fastapi import HTTPException, status

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from app.core.audit import AuditEvent
from app.core.authorization import AuthenticatedPrincipal
from .schemas import ContaBancaria, ContaBancariaInput


class ContasBancariasService:
    """Cadastro de banco e saldo informado; não é conciliação bancária."""

    def __init__(
        self,
        repository: CollectionRepository[ContaBancaria, str] | None = None,
        audit_sink=None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self.audit_sink = audit_sink
        self._items = getattr(self.repository, "_items", {})

    def list(self) -> list[ContaBancaria]:
        return self.repository.list()

    def create(self, data: ContaBancariaInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> ContaBancaria:
        self._ensure_mutation_audit_ready(actor)
        item = ContaBancaria(id=f"cb_shadow_{uuid4().hex}", **data.model_dump())
        if actor is not None:
            self._audited("contas_bancarias:create", item.id, actor, request_id, "add_audited", item)
        else:
            self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: ContaBancariaInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> ContaBancaria:
        self._ensure_mutation_audit_ready(actor)
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta bancária não encontrada.")
        item = ContaBancaria(id=item_id, **data.model_dump())
        if actor is not None:
            self._audited("contas_bancarias:update", item_id, actor, request_id, "replace_audited", item_id, item)
        else:
            self.repository.replace(item_id, item)
        return item

    def delete(self, item_id: str, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> None:
        self._ensure_mutation_audit_ready(actor)
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta bancária não encontrada.")
        if actor is not None:
            self._audited("contas_bancarias:delete", item_id, actor, request_id, "delete_audited", item_id)
        else:
            self.repository.delete(item_id)

    def _ensure_mutation_audit_ready(self, actor) -> None:
        if self.audit_sink is not None and actor is None:
            raise HTTPException(status_code=403, detail="Identidade autenticada obrigatória para operações auditadas de contas bancárias.")

    def _audited(self, action, entity_id, actor, request_id, method, *args):
        if not isinstance(actor, AuthenticatedPrincipal) or actor.account_status != "Ativo" or not actor.subject.strip():
            raise HTTPException(status_code=403, detail="Ator administrativo inválido.")
        operation = getattr(self.repository, method, None)
        if not callable(operation) or not callable(getattr(self.audit_sink, "append_in_transaction", None)):
            raise HTTPException(status_code=503, detail="Persistência e auditoria transacional indisponíveis.")
        event = AuditEvent(actor_subject=actor.subject.strip(), action=action, entity_type="conta_bancaria", entity_id=entity_id, request_id=request_id)
        if method == "replace_audited":
            operation(args[0], args[1], event, self.audit_sink)
        elif method == "add_audited":
            operation(args[0], event, self.audit_sink)
        else:
            operation(args[0], event, self.audit_sink)


contas_bancarias_service = ContasBancariasService()
