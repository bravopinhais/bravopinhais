from fastapi import APIRouter, Depends, Request, status

from app.core.authorization import AuthenticatedPrincipal, require_capability_dependency
from .schemas import Documento, DocumentoInput, DocumentoResumo
from .service import DocumentosService

router = APIRouter(prefix="/api/v1/documentos", tags=["Gestão de Documentos"])


def get_service(request: Request) -> DocumentosService:
    return request.app.state.services.documentos


@router.get(
    "",
    response_model=list[DocumentoResumo],
    dependencies=[Depends(require_capability_dependency("documentos:read"))],
)
def list_documents(request: Request):
    return get_service(request).list_metadata()


@router.get(
    "/{item_id}",
    response_model=Documento,
    dependencies=[Depends(require_capability_dependency("documentos:read"))],
)
def get_document(item_id: str, request: Request):
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
