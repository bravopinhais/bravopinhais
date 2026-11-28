from fastapi import APIRouter, Depends, Request, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency

from .schemas import ContaBancaria, ContaBancariaInput
from .service import ContasBancariasService

router = APIRouter(prefix="/api/v1/contas-bancarias", tags=["Contas Bancárias"])

read_access = Depends(require_capability_dependency("contas_bancarias:read"))
create_access = Depends(require_capability_dependency("contas_bancarias:create"))
update_access = Depends(require_capability_dependency("contas_bancarias:update"))
delete_access = Depends(require_capability_dependency("contas_bancarias:delete"))


def get_service(request: Request) -> ContasBancariasService:
    return request.app.state.services.contas_bancarias


@router.get("", response_model=list[ContaBancaria], dependencies=[read_access])
def list_accounts(request: Request) -> list[ContaBancaria]:
    return get_service(request).list()


@router.post("", response_model=ContaBancaria, status_code=status.HTTP_201_CREATED, dependencies=[create_access])
def create_account(request: Request, data: ContaBancariaInput, principal: AuthenticatedPrincipal = Depends(require_capability_dependency("contas_bancarias:create"))) -> ContaBancaria:
    return get_service(request).create(data, actor=principal, request_id=getattr(request.state, "request_id", None))


@router.put("/{item_id}", response_model=ContaBancaria, dependencies=[update_access])
def update_account(request: Request, item_id: str, data: ContaBancariaInput, principal: AuthenticatedPrincipal = Depends(require_capability_dependency("contas_bancarias:update"))) -> ContaBancaria:
    return get_service(request).update(item_id, data, actor=principal, request_id=getattr(request.state, "request_id", None))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[delete_access])
def delete_account(request: Request, item_id: str, principal: AuthenticatedPrincipal = Depends(require_capability_dependency("contas_bancarias:delete"))) -> None:
    get_service(request).delete(item_id, actor=principal, request_id=getattr(request.state, "request_id", None))
