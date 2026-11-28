from collections.abc import Callable
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.core.audit import AuditEvent
from app.core.authorization import AuthenticatedPrincipal
from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import Categoria, CategoriaInput


class CategoriasService:
    def __init__(
        self,
        repository: CollectionRepository[Categoria, str] | None = None,
        has_document_references: Callable[[str], bool] | None = None,
        audit_sink: Any | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self._has_document_references = has_document_references or (lambda _item_id: False)
        self.audit_sink = audit_sink

    def set_reference_checker(self, checker: Callable[[str], bool]) -> None:
        self._has_document_references = checker

    def list(self) -> list[Categoria]:
        return self.repository.list()

    def get(self, item_id: str) -> Categoria:
        item = self.repository.get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Pasta não encontrada.")
        return item

    def _audit(self, actor: AuthenticatedPrincipal | None, action: str, item_id: str | None, request_id: str | None) -> AuditEvent:
        if not isinstance(actor, AuthenticatedPrincipal) or actor.account_status != "Ativo" or not isinstance(actor.subject, str) or not actor.subject.strip():
            raise HTTPException(status_code=403, detail="Identidade autenticada ativa obrigatória para esta operação.")
        if not isinstance(request_id, str) or not request_id.strip():
            raise HTTPException(status_code=400, detail="Identificador da requisição ausente.")
        if not callable(getattr(self.audit_sink, "append_in_transaction", None)):
            raise HTTPException(status_code=503, detail="Auditoria transacional indisponível.")
        return AuditEvent(
            actor_subject=actor.subject.strip(), action=action,
            entity_type="categoria", entity_id=item_id,
            request_id=request_id.strip(),
        )

    def create(self, data: CategoriaInput, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> Categoria:
        item = Categoria(id=f"cat_shadow_{uuid4().hex}", nome=data.nome)
        if self.audit_sink is not None:
            method = getattr(self.repository, "add_audited", None)
            if not callable(method):
                raise HTTPException(status_code=503, detail="Repositório sem contrato de auditoria transacional.")
            method(item.id, item, self._audit(actor, "categorias:create", item.id, request_id), self.audit_sink)
        else:
            if hasattr(self.repository, "add_audited"):
                raise HTTPException(status_code=503, detail="Auditoria persistente não configurada.")
            self.repository.add(item.id, item)
        return item

    def delete(self, item_id: str, *, actor: AuthenticatedPrincipal | None = None, request_id: str | None = None) -> None:
        self.get(item_id)
        if self._has_document_references(item_id):
            raise HTTPException(status_code=409, detail="Não é possível excluir uma categoria vinculada a documentos.")
        if self.audit_sink is not None:
            method = getattr(self.repository, "delete_audited", None)
            if not callable(method):
                raise HTTPException(status_code=503, detail="Repositório sem contrato de auditoria transacional.")
            method(item_id, self._audit(actor, "categorias:delete", item_id, request_id), self.audit_sink)
        else:
            if hasattr(self.repository, "delete_audited"):
                raise HTTPException(status_code=503, detail="Auditoria persistente não configurada.")
            self.repository.delete(item_id)


categorias_service = CategoriasService()
