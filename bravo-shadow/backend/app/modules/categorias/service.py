from collections.abc import Callable
from uuid import uuid4

from fastapi import HTTPException

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import Categoria, CategoriaInput


class CategoriasService:
    def __init__(
        self,
        repository: CollectionRepository[Categoria, str] | None = None,
        has_document_references: Callable[[str], bool] | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self._has_document_references = has_document_references or (lambda _item_id: False)

    def set_reference_checker(self, checker: Callable[[str], bool]) -> None:
        self._has_document_references = checker

    def list(self) -> list[Categoria]:
        return self.repository.list()

    def get(self, item_id: str) -> Categoria:
        item = self.repository.get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Pasta não encontrada.")
        return item

    def create(self, data: CategoriaInput) -> Categoria:
        item = Categoria(id=f"cat_shadow_{uuid4().hex}", nome=data.nome)
        self.repository.add(item.id, item)
        return item

    def delete(self, item_id: str) -> None:
        self.get(item_id)
        if self._has_document_references(item_id):
            raise HTTPException(
                status_code=409,
                detail="Não é possível excluir uma categoria vinculada a documentos.",
            )
        self.repository.delete(item_id)


categorias_service = CategoriasService()
