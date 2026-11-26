from fastapi import APIRouter, Request
from .schemas import Condominio, CondominioPatch
from .service import CondominioService

router = APIRouter(prefix="/api/v1/condominio", tags=["Condomínio"])


def get_service(request: Request) -> CondominioService:
    return request.app.state.services.condominio


@router.get("", response_model=Condominio)
def get_condominium(request: Request) -> Condominio:
    return get_service(request).get()


@router.put("", response_model=Condominio)
def update_condominium(request: Request, data: CondominioPatch) -> Condominio:
    return get_service(request).update(data)
