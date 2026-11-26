from fastapi import APIRouter, status
from .schemas import Categoria, CategoriaInput
from .service import categorias_service

router = APIRouter(prefix='/api/v1/categorias', tags=['Pastas e Categorias'])

@router.get('', response_model=list[Categoria])
def list_categories(): return categorias_service.list()

@router.post('', response_model=Categoria, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoriaInput): return categorias_service.create(data)

@router.delete('/{item_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_category(item_id: str): categorias_service.delete(item_id)
