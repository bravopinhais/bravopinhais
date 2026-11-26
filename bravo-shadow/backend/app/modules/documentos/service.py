from uuid import uuid4

from fastapi import HTTPException

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import Documento, DocumentoInput


class DocumentosService:
    def __init__(
        self,
        repository: CollectionRepository[Documento, str] | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})

    def list(self) -> list[Documento]:
        return self.repository.list()

    def get(self, item_id: str) -> Documento:
        item = self.repository.get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Documento não encontrado.")
        return item

    def create(self, data: DocumentoInput) -> Documento:
        item = Documento(id=f"doc_shadow_{uuid4().hex}", **data.model_dump())
        self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: DocumentoInput) -> Documento:
        self.get(item_id)
        item = Documento(id=item_id, **data.model_dump())
        self.repository.replace(item_id, item)
        return item

    def delete(self, item_id: str) -> None:
        self.get(item_id)
        self.repository.delete(item_id)


documentos_service = DocumentosService()
