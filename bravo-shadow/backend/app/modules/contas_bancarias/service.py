from uuid import uuid4

from fastapi import HTTPException, status

from .schemas import ContaBancaria, ContaBancariaInput


class ContasBancariasService:
    """Cadastro de banco e saldo informado; não é conciliação bancária."""

    def __init__(self) -> None:
        self._items: dict[str, ContaBancaria] = {}

    def list(self) -> list[ContaBancaria]:
        return list(self._items.values())

    def create(self, data: ContaBancariaInput) -> ContaBancaria:
        item = ContaBancaria(id=f"cb_shadow_{uuid4().hex}", **data.model_dump())
        self._items[item.id] = item
        return item

    def update(self, item_id: str, data: ContaBancariaInput) -> ContaBancaria:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta bancária não encontrada.")
        item = ContaBancaria(id=item_id, **data.model_dump())
        self._items[item_id] = item
        return item

    def delete(self, item_id: str) -> None:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta bancária não encontrada.")
        del self._items[item_id]


contas_bancarias_service = ContasBancariasService()
