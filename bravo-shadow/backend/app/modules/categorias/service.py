from uuid import uuid4

from fastapi import HTTPException

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import Categoria, CategoriaInput


class CategoriasService:
    def __init__(
        self,
        repository: CollectionRepository[Categoria, str] | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})

    def list(self) -> list[Categoria]:
        return self.repository.list()

    def create(self, data: CategoriaInput) -> Categoria:
        item = Categoria(id=f"cat_shadow_{uuid4().hex}", nome=data.nome)
        self.repository.add(item.id, item)
        return item

    def delete(self, item_id: str) -> None:
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=404, detail="Pasta não encontrada.")
        self.repository.delete(item_id)


categorias_service = CategoriasService()
