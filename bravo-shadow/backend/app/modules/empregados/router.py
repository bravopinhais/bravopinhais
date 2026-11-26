from fastapi import APIRouter, Request, status

from .schemas import Empregado, EmpregadoInput
from .service import EmpregadosService

router = APIRouter(prefix="/api/v1/empregados", tags=["Empregados"])


def get_service(request: Request) -> EmpregadosService:
    return request.app.state.services.empregados


@router.get("", response_model=list[Empregado])
def list_employees(request: Request) -> list[Empregado]:
    return get_service(request).list()


@router.post("", response_model=Empregado, status_code=status.HTTP_201_CREATED)
def create_employee(request: Request, data: EmpregadoInput) -> Empregado:
    return get_service(request).create(data)


@router.put("/{item_id}", response_model=Empregado)
def update_employee(request: Request, item_id: str, data: EmpregadoInput) -> Empregado:
    return get_service(request).update(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(request: Request, item_id: str) -> None:
    get_service(request).delete(item_id)
