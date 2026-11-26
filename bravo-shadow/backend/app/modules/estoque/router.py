from fastapi import APIRouter, status
from .schemas import EstoqueInput, EstoqueItem
from .service import estoque_service

router = APIRouter(prefix='/api/v1/estoque', tags=['Estoque e Inventário'])

@router.get('', response_model=list[EstoqueItem])
def list_items(): return estoque_service.list()

@router.post('', response_model=EstoqueItem, status_code=status.HTTP_201_CREATED)
def create_item(data: EstoqueInput): return estoque_service.create(data)

@router.put('/{item_id}', response_model=EstoqueItem)
def update_item(item_id: str, data: EstoqueInput): return estoque_service.update(item_id, data)

@router.delete('/{item_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: str): estoque_service.delete(item_id)
