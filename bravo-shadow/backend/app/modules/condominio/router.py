from fastapi import APIRouter
from .schemas import Condominio, CondominioPatch
from .service import condominio_service

router = APIRouter(prefix="/api/v1/condominio", tags=["Condomínio"])

@router.get("", response_model=Condominio)
def get_condominium() -> Condominio:
    return condominio_service.get()

@router.put("", response_model=Condominio)
def update_condominium(data: CondominioPatch) -> Condominio:
    return condominio_service.update(data)
