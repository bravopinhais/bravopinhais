from fastapi import APIRouter, Depends, Request, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from .schemas import Morador, MoradorInput, MoradorImportBatch, MoradorResumo
from .service import MoradoresService

router = APIRouter(prefix="/api/v1/moradores", tags=["Moradores"])


def get_service(request: Request) -> MoradoresService:
    return request.app.state.services.moradores


@router.get("", response_model=list[MoradorResumo])
def list_residents(
    request: Request,
    bloco: str | None = None,
    busca: str | None = None,
    actor: AuthenticatedPrincipal = Depends(require_capability_dependency("moradores:read")),
) -> list[MoradorResumo]:
    return [MoradorResumo(id=item.id, bloco=item.bloco, apartamento=item.apartamento, nome=item.nome) for item in get_service(request).list(bloco=bloco, busca=busca)]


@router.get("/{item_id}", response_model=Morador)
def get_resident(
    request: Request,
    item_id: str,
    actor: AuthenticatedPrincipal = Depends(require_capability_dependency("moradores:read")),
) -> Morador:
    return get_service(request).get(item_id)


@router.post("", response_model=Morador, status_code=status.HTTP_201_CREATED)
def create_resident(
    request: Request,
    data: MoradorInput,
    actor: AuthenticatedPrincipal = Depends(require_capability_dependency("moradores:create")),
) -> Morador:
    return get_service(request).create(data, actor=actor, request_id=getattr(request.state, 'request_id', None))


@router.put("/{item_id}", response_model=Morador)
def update_resident(
    request: Request,
    item_id: str,
    data: MoradorInput,
    actor: AuthenticatedPrincipal = Depends(require_capability_dependency("moradores:update")),
) -> Morador:
    return get_service(request).update(item_id, data, actor=actor, request_id=getattr(request.state, 'request_id', None))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resident(
    request: Request,
    item_id: str,
    actor: AuthenticatedPrincipal = Depends(require_capability_dependency("moradores:delete")),
) -> None:
    get_service(request).delete(item_id, actor=actor, request_id=getattr(request.state, 'request_id', None))


@router.post("/importar", status_code=status.HTTP_200_OK)
def import_residents(
    request: Request,
    batch: MoradorImportBatch,
    actor: AuthenticatedPrincipal = Depends(require_capability_dependency("moradores:import")),
) -> dict[str, int]:
    return {"importados": get_service(request).import_batch(batch, actor=actor, request_id=getattr(request.state, 'request_id', None))}
