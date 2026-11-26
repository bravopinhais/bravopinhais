from uuid import uuid4
from fastapi import HTTPException
from .schemas import Categoria, CategoriaInput

class CategoriasService:
    def __init__(self): self._items = {}
    def list(self): return list(self._items.values())
    def create(self, data: CategoriaInput):
        item = Categoria(id=f'cat_shadow_{uuid4().hex}', nome=data.nome)
        self._items[item.id] = item
        return item
    def delete(self, item_id: str):
        if item_id not in self._items: raise HTTPException(status_code=404, detail='Pasta não encontrada.')
        del self._items[item_id]

categorias_service = CategoriasService()
