from fastapi import APIRouter, Depends, Request, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from .schemas import Empregado, EmpregadoInput
from .service import EmpregadosService

router = APIRouter(prefix="/api/v1/empregados", tags=["Empregados"])


def get_service(request: Request) -> EmpregadosService:
    return request.app.state.services.empregados


@router.get("", response_model=list[Empregado])
def list_employees(
    request: Request,
    actor: AuthenticatedPrincipal = Depends(require_capability_dependency("empregados:read")),
) -> list[Empregado]:
    return get_service(request).list()


@router.post("", response_model=Empregado, status_code=status.HTTP_201_CREATED)
def create_employee(
    request: Request,
    data: EmpregadoInput,
    actor: AuthenticatedPrincipal = Depends(require_capability_dependency("empregados:create")),
) -> Empregado:
    return get_service(request).create(data, actor=actor, request_id=getattr(request.state, 'request_id', None))


@router.put("/{item_id}", response_model=Empregado)
def update_employee(
    request: Request,
    item_id: str,
    data: EmpregadoInput,
    actor: AuthenticatedPrincipal = Depends(require_capability_dependency("empregados:update")),
) -> Empregado:
    return get_service(request).update(item_id, data, actor=actor, request_id=getattr(request.state, 'request_id', None))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    request: Request,
    item_id: str,
    actor: AuthenticatedPrincipal = Depends(require_capability_dependency("empregados:delete")),
) -> None:
    get_service(request).delete(item_id, actor=actor, request_id=getattr(request.state, 'request_id', None))
