from uuid import uuid4
from fastapi import HTTPException, status
from .schemas import Fornecedor, FornecedorInput

class FornecedoresService:
    def __init__(self) -> None:
        self._items: dict[str, Fornecedor] = {}
    def list(self) -> list[Fornecedor]:
        return list(self._items.values())
    def create(self, data: FornecedorInput) -> Fornecedor:
        item = Fornecedor(id=f"for_shadow_{uuid4().hex}", **data.model_dump())
        self._items[item.id] = item
        return item
    def update(self, item_id: str, data: FornecedorInput) -> Fornecedor:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado.")
        item = Fornecedor(id=item_id, **data.model_dump())
        self._items[item_id] = item
        return item
    def delete(self, item_id: str) -> None:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fornecedor não encontrado.")
        del self._items[item_id]

fornecedores_service = FornecedoresService()
