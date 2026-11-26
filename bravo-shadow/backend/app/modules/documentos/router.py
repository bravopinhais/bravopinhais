from fastapi import APIRouter, Depends, Request, status

from app.core.authorization import require_capability_dependency
from .schemas import Documento, DocumentoInput
from .service import DocumentosService

router = APIRouter(prefix="/api/v1/documentos", tags=["Gestão de Documentos"])


def get_service(request: Request) -> DocumentosService:
    return request.app.state.services.documentos


@router.get(
    "",
    response_model=list[Documento],
    dependencies=[Depends(require_capability_dependency("documentos:read"))],
)
def list_documents(request: Request):
    return get_service(request).list()


@router.get(
    "/{item_id}",
    response_model=Documento,
    dependencies=[Depends(require_capability_dependency("documentos:read"))],
)
def get_document(item_id: str, request: Request):
    return get_service(request).get(item_id)


@router.post(
    "",
    response_model=Documento,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_capability_dependency("documentos:create"))],
)
def create_document(data: DocumentoInput, request: Request):
    return get_service(request).create(data)


@router.put(
    "/{item_id}",
    response_model=Documento,
    dependencies=[Depends(require_capability_dependency("documentos:update"))],
)
def update_document(item_id: str, data: DocumentoInput, request: Request):
    return get_service(request).update(item_id, data)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_capability_dependency("documentos:delete"))],
)
def delete_document(item_id: str, request: Request):
    get_service(request).delete(item_id)
