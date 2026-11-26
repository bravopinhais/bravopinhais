from collections.abc import Callable
from uuid import uuid4

from fastapi import HTTPException

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import EstoqueInput, EstoqueItem


class EstoqueService:
    """Regras de estoque desacopladas do armazenamento."""

    def __init__(
        self,
        repository: CollectionRepository[EstoqueItem, str] | None = None,
        has_movement_references: Callable[[str], bool] | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})
        self._has_movement_references = has_movement_references or (lambda _item_id: False)

    def set_movement_reference_checker(self, checker: Callable[[str], bool]) -> None:
        self._has_movement_references = checker

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
        current = self.get(item_id)
        if self._has_movement_references(item_id) and data.quantidade != current.quantidade:
            raise HTTPException(
                status_code=409,
                detail=(
                    "O saldo deste produto possui histórico de movimentações. "
                    "Altere a quantidade por um acerto de estoque."
                ),
            )
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
        if self._has_movement_references(item_id):
            raise HTTPException(
                status_code=409,
                detail="O produto possui movimentações e não pode ser excluído.",
            )
        self.repository.delete(item_id)


# Compatibilidade temporária para consumidores legados fora dos routers.
# A aplicação FastAPI usa instâncias isoladas criadas em build_storage_services().
estoque_service = EstoqueService()
