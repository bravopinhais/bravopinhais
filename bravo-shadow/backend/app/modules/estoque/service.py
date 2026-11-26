from uuid import uuid4

from fastapi import HTTPException

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import EstoqueInput, EstoqueItem


class EstoqueService:
    """Regras de estoque desacopladas do armazenamento."""

    def __init__(self, repository: CollectionRepository[EstoqueItem, str] | None = None) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})

    def list(self) -> list[EstoqueItem]:
        return self.repository.list()

    def get(self, item_id: str) -> EstoqueItem:
        item = self.repository.get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Produto não encontrado.")
        return item

    def create(self, data: EstoqueInput) -> EstoqueItem:
        item = EstoqueItem(id=f"est_shadow_{uuid4().hex}", **data.model_dump())
        self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: EstoqueInput) -> EstoqueItem:
        self.get(item_id)
        item = EstoqueItem(id=item_id, **data.model_dump())
        self.repository.replace(item_id, item)
        return item

    def update_quantity(self, item_id: str, quantity: int) -> EstoqueItem:
        product = self.get(item_id)
        updated = product.model_copy(update={"quantidade": quantity})
        self.repository.replace(item_id, updated)
        return updated

    def delete(self, item_id: str) -> None:
        self.get(item_id)
        self.repository.delete(item_id)


# Compatibilidade temporária para consumidores legados fora dos routers.
# A aplicação FastAPI usa instâncias isoladas criadas em build_storage_services().
estoque_service = EstoqueService()
