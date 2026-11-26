from uuid import uuid4

from fastapi import HTTPException, status

from app.core.repositories import CollectionRepository, InMemoryCollectionRepository
from .schemas import ContaBancaria, ContaBancariaInput


class ContasBancariasService:
    """Cadastro de banco e saldo informado; não é conciliação bancária."""

    def __init__(
        self,
        repository: CollectionRepository[ContaBancaria, str] | None = None,
    ) -> None:
        self.repository = repository if repository is not None else InMemoryCollectionRepository()
        self._items = getattr(self.repository, "_items", {})

    def list(self) -> list[ContaBancaria]:
        return self.repository.list()

    def create(self, data: ContaBancariaInput) -> ContaBancaria:
        item = ContaBancaria(id=f"cb_shadow_{uuid4().hex}", **data.model_dump())
        self.repository.add(item.id, item)
        return item

    def update(self, item_id: str, data: ContaBancariaInput) -> ContaBancaria:
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta bancária não encontrada.")
        item = ContaBancaria(id=item_id, **data.model_dump())
        self.repository.replace(item_id, item)
        return item

    def delete(self, item_id: str) -> None:
        if not self.repository.exists(item_id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta bancária não encontrada.")
        self.repository.delete(item_id)


contas_bancarias_service = ContasBancariasService()
