from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from app.core.read_audit import audit_read
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
    service = get_service(request)
    audit_read(request, service, _principal, "usuarios:list", "usuario")
    return service.list()


@router.get("/{item_id}", response_model=Usuario)
def get_user(
    request: Request,
    item_id: str,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("usuarios:read")),
) -> Usuario:
    service = get_service(request)
    audit_read(request, service, _principal, "usuarios:read", "usuario", item_id)
    return service.get(item_id)


@router.post("", response_model=Usuario, status_code=status.HTTP_201_CREATED)
def create_user(
    request: Request,
    data: UsuarioCadastroInput,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("usuarios:create")),
) -> Usuario:
    return get_service(request).create_cadastral(data, actor=principal, request_id=getattr(request.state, "request_id", None))


@router.put("/{item_id}", response_model=Usuario)
def update_user(
    request: Request,
    item_id: str,
    data: UsuarioDadosCadastraisUpdateInput,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("usuarios:update")),
) -> Usuario:
    return get_service(request).update_cadastral(item_id, data, actor=principal, request_id=getattr(request.state, "request_id", None))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    request: Request,
    item_id: str,
    _principal: AuthenticatedPrincipal = Depends(require_capability_dependency("usuarios:delete")),
) -> None:
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Exclusão física indisponível. Use a operação de desativação lógica.",
    )



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
        actor=principal,
        request_id=getattr(request.state, "request_id", None),
    )
