from fastapi import APIRouter, status
from .schemas import Acerto, AcertoInput
from .service import acertos_estoque_service

router = APIRouter(prefix='/api/v1/acertos-estoque', tags=['Acertos de Estoque'])

@router.get('', response_model=list[Acerto])
def list_adjustments(): return acertos_estoque_service.list()

@router.post('', response_model=Acerto, status_code=status.HTTP_201_CREATED)
def create_adjustment(data: AcertoInput): return acertos_estoque_service.create(data)

@router.delete('/{item_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_adjustment(item_id: str): acertos_estoque_service.delete(item_id)
