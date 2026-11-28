from fastapi import APIRouter, Depends, Request, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from app.core.audit import AuditEvent
from fastapi import HTTPException
from .schemas import Documento, DocumentoInput, DocumentoResumo
from .service import DocumentosService

router = APIRouter(prefix="/api/v1/documentos", tags=["Gestão de Documentos"])


def get_service(request: Request) -> DocumentosService:
    return request.app.state.services.documentos


def audit_document_read(
    request: Request,
    principal: AuthenticatedPrincipal,
    action: str,
    item_id: str | None = None,
) -> None:
    """Registra acesso a documentos sem incluir título, nome ou conteúdo."""
    sink = getattr(get_service(request), "audit_sink", None)
    if sink is None:
        if getattr(request.app.state, "storage_backend", None) == "postgres":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Auditoria indisponível. A consulta não foi concluída.",
            )
        return
    event = AuditEvent(
        actor_subject=principal.subject.strip(),
        action=f"documentos:{action}",
        entity_type="documento",
        entity_id=item_id,
        outcome="success",
        request_id=getattr(request.state, "request_id", None),
    )
    try:
        sink.append(event)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auditoria indisponível. A consulta ao documento não foi concluída.",
        ) from exc


@router.get(
    "",
    response_model=list[DocumentoResumo],
    dependencies=[Depends(require_capability_dependency("documentos:read"))],
)
def list_documents(
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("documentos:read")),
):
    audit_document_read(request, principal, "list")
    return get_service(request).list_metadata()


@router.get(
    "/{item_id}",
    response_model=Documento,
    dependencies=[Depends(require_capability_dependency("documentos:read"))],
)
def get_document(
    item_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("documentos:read")),
):
    audit_document_read(request, principal, "read", item_id)
    return get_service(request).get(item_id)


@router.post(
    "",
    response_model=DocumentoResumo,
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    data: DocumentoInput,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("documentos:create")),
):
    return get_service(request).create(
        data, actor=principal, request_id=getattr(request.state, "request_id", None)
    )


@router.put(
    "/{item_id}",
    response_model=DocumentoResumo,
)
def update_document(
    item_id: str,
    data: DocumentoInput,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("documentos:update")),
):
    return get_service(request).update(
        item_id, data, actor=principal, request_id=getattr(request.state, "request_id", None)
    )


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    item_id: str,
    request: Request,
    principal: AuthenticatedPrincipal = Depends(require_capability_dependency("documentos:delete")),
):
    get_service(request).delete(
        item_id, actor=principal, request_id=getattr(request.state, "request_id", None)
    )
