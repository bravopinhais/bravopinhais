from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from app.modules.categorias.service import CategoriasService
from .schemas import Documento, DocumentoInput, DocumentoResumo


class DocumentosService:
    def __init__(
        self,
        repository: CollectionRepository[Documento, str] | None = None,
        category_service: CategoriasService | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self.category_service = category_service

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

    def create(self, data: DocumentoInput) -> Documento:
        item = self._build_document(data, f"doc_shadow_{uuid4().hex}")
        self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: DocumentoInput) -> Documento:
        self.get(item_id)
        item = self._build_document(data, item_id)
        self.repository.replace(item_id, item)
        return item

    def delete(self, item_id: str) -> None:
        self.get(item_id)
        self.repository.delete(item_id)


documentos_service = DocumentosService()
