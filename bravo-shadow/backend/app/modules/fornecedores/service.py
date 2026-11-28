from uuid import uuid4

from app.core.authorization import AuthenticatedPrincipal
from app.core.audit import AuditEvent

from fastapi import HTTPException, status

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import Fornecedor, FornecedorInput


class FornecedoresService:
    def __init__(
        self,
        repository: CollectionRepository[Fornecedor, str] | None = None,
        audit_sink=None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self.audit_sink = audit_sink

    def _require_audited_write(self, actor: AuthenticatedPrincipal | None) -> None:
        if self.audit_sink is not None and (
            not isinstance(actor, AuthenticatedPrincipal)
            or actor.account_status != "Ativo"
            or not isinstance(actor.subject, str)
            or not actor.subject.strip()
        ):
            raise HTTPException(status_code=403, detail="Identidade interna ativa obrigatória para alterar este cadastro.")

    def _audit_event(self, actor: AuthenticatedPrincipal, action: str, item_id: str, request_id: str | None) -> AuditEvent:
        return AuditEvent(actor_subject=actor.subject.strip(), action=f"fornecedores:{action}", entity_type="fornecedor", entity_id=item_id, outcome="success", request_id=request_id)

    def _audited_repository(self, method: str):
        operation = getattr(self.repository, method, None)
        if self.audit_sink is not None and (not callable(operation) or not callable(getattr(self.audit_sink, "append_in_transaction", None))):
            raise HTTPException(status_code=503, detail="Persistência e auditoria transacional indisponíveis. Nenhuma alteração foi confirmada.")
        return operation

    def list(self) -> list[Fornecedor]:
        return self.repository.list()

    def create(self, data: FornecedorInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> Fornecedor:
        self._require_audited_write(actor)
        item = Fornecedor(id=f"for_shadow_{uuid4().hex}", **data.model_dump())
        if self.audit_sink is not None:
            operation = self._audited_repository("add_audited")
            operation(item, self._audit_event(actor, "create", item.id, request_id), self.audit_sink)
        else:
            self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: FornecedorInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> Fornecedor:
        self._require_audited_write(actor)
        item = Fornecedor(id=item_id, **data.model_dump())
        if self.audit_sink is not None:
            operation = self._audited_repository("replace_audited")
            operation(item_id, item, self._audit_event(actor, "update", item_id, request_id), self.audit_sink)
        else:
            if not self.repository.exists(item_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado.")
            self.repository.replace(item_id, item)
        return item

    def delete(self, item_id: str, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> None:
        self._require_audited_write(actor)
        if self.audit_sink is not None:
            operation = self._audited_repository("delete_audited")
            operation(item_id, self._audit_event(actor, "delete", item_id, request_id), self.audit_sink)
        else:
            if not self.repository.exists(item_id):
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado.")
            self.repository.delete(item_id)


fornecedores_service = FornecedoresService()
