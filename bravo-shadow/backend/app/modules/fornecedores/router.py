from fastapi import APIRouter, Depends, Request, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from .schemas import Fornecedor, FornecedorInput
from .service import FornecedoresService

router = APIRouter(prefix="/api/v1/fornecedores", tags=["Fornecedores"])


def get_service(request: Request) -> FornecedoresService:
    return request.app.state.services.fornecedores


@router.get("", response_model=list[Fornecedor])
def list_suppliers(
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("fornecedores:read")),
) -> list[Fornecedor]:
    return get_service(request).list()


@router.post("", response_model=Fornecedor, status_code=status.HTTP_201_CREATED)
def create_supplier(
    request: Request,
    data: FornecedorInput,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("fornecedores:create")),
) -> Fornecedor:
    return get_service(request).create(data)


@router.put("/{item_id}", response_model=Fornecedor)
def update_supplier(
    request: Request,
    item_id: str,
    data: FornecedorInput,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("fornecedores:update")),
) -> Fornecedor:
    return get_service(request).update(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    request: Request,
    item_id: str,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("fornecedores:delete")),
) -> None:
    get_service(request).delete(item_id)
