from fastapi import APIRouter, Depends, Request, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency

from .schemas import Categoria, CategoriaInput
from .service import CategoriasService

router = APIRouter(prefix="/api/v1/categorias", tags=["Pastas e Categorias"])


def get_service(request: Request) -> CategoriasService:
    return request.app.state.services.categorias


@router.get("", response_model=list[Categoria])
def list_categories(
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("categorias:read")),
):
    return get_service(request).list()


@router.post("", response_model=Categoria, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoriaInput,
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("categorias:create")),
):
    return get_service(request).create(data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    item_id: str,
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("categorias:delete")),
):
    get_service(request).delete(item_id)
