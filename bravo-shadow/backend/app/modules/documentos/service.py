from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from app.core.audit import AuditEvent
from app.core.authorization import AuthenticatedPrincipal
from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from app.modules.categorias.service import CategoriasService
from .schemas import Documento, DocumentoInput, DocumentoResumo


class DocumentosService:
    def __init__(
        self,
        repository: CollectionRepository[Documento, str] | None = None,
        category_service: CategoriasService | None = None,
        audit_sink: Any | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self.category_service = category_service
        self.audit_sink = audit_sink

    def list(self) -> list[Documento]:
        return self.repository.list()

    def list_metadata(self) -> list[DocumentoResumo]:
        metadata_reader = getattr(self.repository, "list_metadata", None)
        if callable(metadata_reader):
            return metadata_reader()
        return [
            DocumentoResumo(
                id=item.id,
                pasta=item.pasta,
                categoriaId=item.categoriaId,
                titulo=item.titulo,
                nomeArquivo=item.nomeArquivo,
            )
            for item in self.repository.list()
        ]

    def get(self, item_id: str) -> Documento:
        item = self.repository.get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Documento não encontrado.")
        return item

    def has_category_reference(self, category_id: str) -> bool:
        return any(item.categoriaId == category_id for item in self.repository.list())

    def _build_document(self, data: DocumentoInput, item_id: str) -> Documento:
        values = data.model_dump()
        if data.categoriaId:
            if self.category_service is None:
                raise HTTPException(
                    status_code=400,
                    detail="Vínculo de categoria não está configurado.",
                )
            category = self.category_service.get(data.categoriaId)
            values["pasta"] = category.nome
        return Documento(id=item_id, **values)

    def _audit(
        self, actor: AuthenticatedPrincipal | None, action: str,
        item_id: str, request_id: str | None,
    ) -> AuditEvent:
        if (
            not isinstance(actor, AuthenticatedPrincipal)
            or actor.account_status != "Ativo"
            or not isinstance(actor.subject, str)
            or not actor.subject.strip()
        ):
            raise HTTPException(status_code=403, detail="Identidade autenticada ativa obrigatória para esta operação.")
        if not isinstance(request_id, str) or not request_id.strip():
            raise HTTPException(status_code=400, detail="Identificador da requisição ausente.")
        if not callable(getattr(self.audit_sink, "append_in_transaction", None)):
            raise HTTPException(status_code=503, detail="Auditoria transacional indisponível.")
        return AuditEvent(
            actor_subject=actor.subject.strip(),
            action=action,
            entity_type="documento",
            entity_id=item_id,
            request_id=request_id.strip(),
        )

    def create(
        self, data: DocumentoInput, *,
        actor: AuthenticatedPrincipal | None = None,
        request_id: str | None = None,
    ) -> Documento:
        item = self._build_document(data, f"doc_shadow_{uuid4().hex}")
        if self.audit_sink is not None:
            method = getattr(self.repository, "add_audited", None)
            if not callable(method):
                raise HTTPException(status_code=503, detail="Repositório sem contrato de auditoria transacional.")
            method(item.id, item, self._audit(actor, "documentos:create", item.id, request_id), self.audit_sink)
        else:
            if hasattr(self.repository, "add_audited"):
                raise HTTPException(status_code=503, detail="Auditoria persistente não configurada.")
            self.repository.add(item.id, item)
        return item

    def update(
        self, item_id: str, data: DocumentoInput, *,
        actor: AuthenticatedPrincipal | None = None,
        request_id: str | None = None,
    ) -> Documento:
        self.get(item_id)
        item = self._build_document(data, item_id)
        if self.audit_sink is not None:
            method = getattr(self.repository, "replace_audited", None)
            if not callable(method):
                raise HTTPException(status_code=503, detail="Repositório sem contrato de auditoria transacional.")
            method(item_id, item, self._audit(actor, "documentos:update", item_id, request_id), self.audit_sink)
        else:
            if hasattr(self.repository, "replace_audited"):
                raise HTTPException(status_code=503, detail="Auditoria persistente não configurada.")
            self.repository.replace(item_id, item)
        return item

    def delete(
        self, item_id: str, *,
        actor: AuthenticatedPrincipal | None = None,
        request_id: str | None = None,
    ) -> None:
        self.get(item_id)
        if self.audit_sink is not None:
            method = getattr(self.repository, "delete_audited", None)
            if not callable(method):
                raise HTTPException(status_code=503, detail="Repositório sem contrato de auditoria transacional.")
            method(item_id, self._audit(actor, "documentos:delete", item_id, request_id), self.audit_sink)
        else:
            if hasattr(self.repository, "delete_audited"):
                raise HTTPException(status_code=503, detail="Auditoria persistente não configurada.")
            self.repository.delete(item_id)


documentos_service = DocumentosService()
