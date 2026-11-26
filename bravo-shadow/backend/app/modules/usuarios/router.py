from fastapi import APIRouter, status
from .schemas import Usuario, UsuarioInput
from .service import usuarios_service

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuários"])

@router.get("", response_model=list[Usuario])
def list_users() -> list[Usuario]:
    return usuarios_service.list()

@router.get("/{item_id}", response_model=Usuario)
def get_user(item_id: str) -> Usuario:
    return usuarios_service.get(item_id)

@router.post("", response_model=Usuario, status_code=status.HTTP_201_CREATED)
def create_user(data: UsuarioInput) -> Usuario:
    return usuarios_service.create(data)

@router.put("/{item_id}", response_model=Usuario)
def update_user(item_id: str, data: UsuarioInput) -> Usuario:
    return usuarios_service.update(item_id, data)

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(item_id: str) -> None:
    usuarios_service.delete(item_id)
