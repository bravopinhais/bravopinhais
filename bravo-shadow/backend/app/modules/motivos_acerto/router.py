from fastapi import APIRouter, Request, status

from .schemas import MotivoAcerto, MotivoAcertoInput
from .service import MotivosAcertoService

router = APIRouter(
    prefix="/api/v1/motivos-acerto-estoque",
    tags=["Motivos de Acerto de Estoque"],
)


def get_service(request: Request) -> MotivosAcertoService:
    return request.app.state.services.motivos_acerto


@router.get("", response_model=list[MotivoAcerto])
def list_reasons(request: Request):
    return get_service(request).list()


@router.post("", response_model=MotivoAcerto, status_code=status.HTTP_201_CREATED)
def create_reason(data: MotivoAcertoInput, request: Request):
    return get_service(request).create(data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reason(item_id: str, request: Request):
    get_service(request).delete(item_id)
