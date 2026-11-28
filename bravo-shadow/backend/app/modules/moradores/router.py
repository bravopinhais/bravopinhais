from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from app.core.audit import AuditEvent
from .schemas import Morador, MoradorInput, MoradorImportBatch, MoradorResumo
from .service import MoradoresService

router = APIRouter(prefix="/api/v1/moradores", tags=["Moradores"])


def get_service(request: Request) -> MoradoresService:
    return request.app.state.services.moradores


def audit_resident_read(
    request: Request,
    actor: AuthenticatedPrincipal,
    action: str,
    item_id: str | None = None,
) -> None:
    """Registra consultas a dados pessoais sem armazenar filtros ou conteúdo."""
    sink = getattr(get_service(request), "audit_sink", None)
    if sink is None:
        return
    event = AuditEvent(
        actor_subject=actor.subject.strip(),
        action=f"moradores:{action}",
        entity_type="morador",
        entity_id=item_id,
        outcome="success",
        request_id=getattr(request.state, "request_id", None),
    )
    try:
        sink.append(event)
    except Exception as exc:
        # Não expor dados pessoais quando a auditoria persistente está indisponível.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auditoria indisponível. A consulta não foi concluída.",
        ) from exc


@router.get("", response_model=list[MoradorResumo])
def list_residents(
    request: Request,
    bloco: str | None = None,
    busca: str | None = None,
    actor: AuthenticatedPrincipal = Depends(require_capability_dependency("moradores:read")),
) -> list[MoradorResumo]:
    audit_resident_read(request, actor, "list")
    return [MoradorResumo(id=item.id, bloco=item.bloco, apartamento=item.apartamento, nome=item.nome) for item in get_service(request).list(bloco=bloco, busca=busca)]


@router.get("/{item_id}", response_model=Morador)
def get_resident(
    request: Request,
    item_id: str,
    actor: AuthenticatedPrincipal = Depends(require_capability_dependency("moradores:read")),
) -> Morador:
    audit_resident_read(request, actor, "read", item_id)
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
