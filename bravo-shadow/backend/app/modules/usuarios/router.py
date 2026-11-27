from fastapi import APIRouter, Depends, Request, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from .schemas import Usuario, UsuarioCadastroInput, UsuarioDadosCadastraisUpdateInput
from .service import UsuariosService

router = APIRouter(prefix="/api/v1/usuarios", tags=["Usuários"])


def get_service(request: Request) -> UsuariosService:
    return request.app.state.services.usuarios


@router.get("", response_model=list[Usuario])
def list_users(
    request: Request,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("usuarios:read")),
) -> list[Usuario]:
    return get_service(request).list()


@router.get("/{item_id}", response_model=Usuario)
def get_user(
    request: Request,
    item_id: str,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("usuarios:read")),
) -> Usuario:
    return get_service(request).get(item_id)


@router.post("", response_model=Usuario, status_code=status.HTTP_201_CREATED)
def create_user(
    request: Request,
    data: UsuarioCadastroInput,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("usuarios:create")),
) -> Usuario:
    return get_service(request).create_cadastral(data)


@router.put("/{item_id}", response_model=Usuario)
def update_user(
    request: Request,
    item_id: str,
    data: UsuarioDadosCadastraisUpdateInput,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("usuarios:update")),
) -> Usuario:
    return get_service(request).update_cadastral(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    request: Request,
    item_id: str,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("usuarios:delete")),
) -> None:
    get_service(request).delete(item_id)



@router.post("/{item_id}/desativar", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    request: Request,
    item_id: str,
    principal: AuthenticatedPrincipal = Depends(
        require_capability_dependency("usuarios:deactivate")
    ),
) -> None:
    get_service(request).deactivate(
        item_id,
        actor_subject=principal.subject,
        actor_email=principal.email,
    )
