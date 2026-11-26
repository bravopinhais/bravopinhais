from datetime import datetime
from uuid import uuid4
from fastapi import HTTPException
from .schemas import Acerto, AcertoInput
from app.modules.estoque.service import estoque_service

class AcertosEstoqueService:
    def __init__(self): self._items = {}
    def list(self): return list(self._items.values())
    def create(self, data: AcertoInput):
        product = estoque_service.get(data.produtoId)
        current = product.quantidade
        if data.tipo == 'Saída' and data.quantidade > current:
            raise HTTPException(status_code=409, detail='Quantidade de saída superior ao saldo disponível.')
        new_quantity = current + data.quantidade if data.tipo == 'Entrada' else current - data.quantidade
        updated = product.model_copy(update={'quantidade': new_quantity})
        estoque_service._items[product.id] = updated
        item = Acerto(id=f'ac_shadow_{uuid4().hex}', data=datetime.now().astimezone().isoformat(), **data.model_dump())
        self._items[item.id] = item
        return item
    def delete(self, item_id):
        if item_id not in self._items: raise HTTPException(status_code=404, detail='Acerto não encontrado.')
        # Mantém paridade com o original: apagar o histórico não reverte o saldo.
        del self._items[item_id]

acertos_estoque_service = AcertosEstoqueService()
