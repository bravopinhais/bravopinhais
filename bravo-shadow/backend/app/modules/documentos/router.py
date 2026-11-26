from fastapi import APIRouter, status
from .schemas import Documento, DocumentoInput
from .service import documentos_service

router = APIRouter(prefix='/api/v1/documentos', tags=['Gestão de Documentos'])

@router.get('', response_model=list[Documento])
def list_documents(): return documentos_service.list()

@router.get('/{item_id}', response_model=Documento)
def get_document(item_id: str): return documentos_service.get(item_id)

@router.post('', response_model=Documento, status_code=status.HTTP_201_CREATED)
def create_document(data: DocumentoInput): return documentos_service.create(data)

@router.put('/{item_id}', response_model=Documento)
def update_document(item_id: str, data: DocumentoInput): return documentos_service.update(item_id, data)

@router.delete('/{item_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_document(item_id: str): documentos_service.delete(item_id)
