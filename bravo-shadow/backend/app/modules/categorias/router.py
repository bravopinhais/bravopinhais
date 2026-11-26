from fastapi import APIRouter, Request, status

from .schemas import Categoria, CategoriaInput
from .service import CategoriasService

router = APIRouter(prefix="/api/v1/categorias", tags=["Pastas e Categorias"])


def get_service(request: Request) -> CategoriasService:
    return request.app.state.services.categorias


@router.get("", response_model=list[Categoria])
def list_categories(request: Request):
    return get_service(request).list()


@router.post("", response_model=Categoria, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoriaInput, request: Request):
    return get_service(request).create(data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(item_id: str, request: Request):
    get_service(request).delete(item_id)
