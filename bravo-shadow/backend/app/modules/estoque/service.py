from uuid import uuid4
from fastapi import HTTPException
from .schemas import EstoqueInput, EstoqueItem

class EstoqueService:
    def __init__(self): self._items = {}
    def list(self): return list(self._items.values())
    def get(self, item_id):
        if item_id not in self._items: raise HTTPException(status_code=404, detail='Produto não encontrado.')
        return self._items[item_id]
    def create(self, data: EstoqueInput):
        item = EstoqueItem(id=f'est_shadow_{uuid4().hex}', **data.model_dump())
        self._items[item.id] = item
        return item
    def update(self, item_id, data: EstoqueInput):
        self.get(item_id)
        item = EstoqueItem(id=item_id, **data.model_dump())
        self._items[item_id] = item
        return item
    def delete(self, item_id):
        self.get(item_id)
        del self._items[item_id]

estoque_service = EstoqueService()
