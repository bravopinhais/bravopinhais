from fastapi import APIRouter, status
from .schemas import MotivoAcerto, MotivoAcertoInput
from .service import motivos_acerto_service

router = APIRouter(prefix='/api/v1/motivos-acerto-estoque', tags=['Motivos de Acerto de Estoque'])

@router.get('', response_model=list[MotivoAcerto])
def list_reasons(): return motivos_acerto_service.list()

@router.post('', response_model=MotivoAcerto, status_code=status.HTTP_201_CREATED)
def create_reason(data: MotivoAcertoInput): return motivos_acerto_service.create(data)

@router.delete('/{item_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_reason(item_id: str): motivos_acerto_service.delete(item_id)
