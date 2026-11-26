from uuid import uuid4

from fastapi import HTTPException, status

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import FinanceiroInput, FinanceiroTitulo


class FinanceiroService:
    """Regras financeiras independentes do mecanismo de persistência."""

    def __init__(self, repository: CollectionRepository[FinanceiroTitulo, str] | None = None) -> None:
        self.repository = repository or InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})

    def list(self) -> list[FinanceiroTitulo]:
        return self.repository.list()

    def create(self, data: FinanceiroInput) -> FinanceiroTitulo:
        item = FinanceiroTitulo(id=f"fin_shadow_{uuid4().hex}", **data.model_dump())
        self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: FinanceiroInput) -> FinanceiroTitulo:
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Título não encontrado.")
        item = FinanceiroTitulo(id=item_id, **data.model_dump())
        self.repository.replace(item_id, item)
        return item

    def delete(self, item_id: str) -> None:
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Título não encontrado.")
        self.repository.delete(item_id)

    def has_plan_account_reference(self, account_id: str) -> bool:
        return any(item.planoContaId == account_id for item in self.repository.list())


financeiro_service = FinanceiroService()
