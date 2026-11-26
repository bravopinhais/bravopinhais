from uuid import uuid4
from fastapi import HTTPException, status
from .schemas import Conselheiro, ConselheiroInput

class ConselheirosService:
    def __init__(self) -> None:
        self._items: dict[str, Conselheiro] = {}
    def list(self) -> list[Conselheiro]:
        return list(self._items.values())
    def create(self, data: ConselheiroInput) -> Conselheiro:
        item = Conselheiro(id=f"cons_shadow_{uuid4().hex}", **data.model_dump())
        self._items[item.id] = item
        return item
    def update(self, item_id: str, data: ConselheiroInput) -> Conselheiro:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conselheiro não encontrado.")
        item = Conselheiro(id=item_id, **data.model_dump())
        self._items[item_id] = item
        return item
    def delete(self, item_id: str) -> None:
        if item_id not in self._items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conselheiro não encontrado.")
        del self._items[item_id]

conselheiros_service = ConselheirosService()
