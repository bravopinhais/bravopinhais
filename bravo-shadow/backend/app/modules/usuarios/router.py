from fastapi import APIRouter, Request, status
from .schemas import Usuario, UsuarioInput
from .service import UsuariosService

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuários"])


def get_service(request: Request) -> UsuariosService:
    return request.app.state.services.usuarios


@router.get("", response_model=list[Usuario])
def list_users(request: Request) -> list[Usuario]:
    return get_service(request).list()


@router.get("/{item_id}", response_model=Usuario)
def get_user(request: Request, item_id: str) -> Usuario:
    return get_service(request).get(item_id)


@router.post("", response_model=Usuario, status_code=status.HTTP_201_CREATED)
def create_user(request: Request, data: UsuarioInput) -> Usuario:
    return get_service(request).create(data)


@router.put("/{item_id}", response_model=Usuario)
def update_user(request: Request, item_id: str, data: UsuarioInput) -> Usuario:
    return get_service(request).update(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(request: Request, item_id: str) -> None:
    get_service(request).delete(item_id)
