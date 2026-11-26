from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.authorization import (
    AuthenticatedPrincipal,
    require_capability_dependency,
)
from .schemas import Usuario, UsuarioInput
from .service import UsuariosService

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuários"])


def get_service(request: Request) -> UsuariosService:
    return request.app.state.services.usuarios


@router.get("", response_model=list[Usuario])
def list_users(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(
        require_capability_dependency("usuarios:read")
    ),
) -> list[Usuario]:
    return get_service(request).list()


@router.get("/{item_id}", response_model=Usuario)
def get_user(
    request: Request,
    item_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_capability_dependency("usuarios:read")
    ),
) -> Usuario:
    return get_service(request).get(item_id)


@router.post("", response_model=Usuario, status_code=status.HTTP_201_CREATED)
def create_user(
    request: Request,
    data: UsuarioInput,
    principal: AuthenticatedPrincipal = Depends(
        require_capability_dependency("usuarios:create")
    ),
) -> Usuario:
    return get_service(request).create(data)


@router.put("/{item_id}", response_model=Usuario)
def update_user(
    request: Request,
    item_id: str,
    data: UsuarioInput,
    principal: AuthenticatedPrincipal = Depends(
        require_capability_dependency("usuarios:update")
    ),
) -> Usuario:
    service = get_service(request)
    current = service.get(item_id)

    # A identidade vem do token validado, nunca do corpo enviado pelo cliente.
    # Impede que um administrador altere o próprio vínculo, perfil ou status.
    if current.email.strip().lower() == principal.email.strip().lower():
        protected_fields_changed = (
            data.email.strip().lower() != current.email.strip().lower()
            or data.perfil != current.perfil
            or data.status != current.status
        )
        if protected_fields_changed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Não é permitido alterar o próprio e-mail, perfil ou status.",
            )

    return service.update(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    request: Request,
    item_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_capability_dependency("usuarios:delete")
    ),
) -> None:
    service = get_service(request)
    target = service.get(item_id)
    if target.email.strip().lower() == principal.email.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Não é permitido excluir o próprio usuário.",
        )
    service.delete(item_id)
