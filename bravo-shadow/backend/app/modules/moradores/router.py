from fastapi import APIRouter, Request, status

from .schemas import Morador, MoradorInput, MoradorImportBatch
from .service import MoradoresService

router = APIRouter(prefix="/api/v1/moradores", tags=["Moradores"])


def get_service(request: Request) -> MoradoresService:
    return request.app.state.services.moradores


@router.get("", response_model=list[Morador])
def list_residents(request: Request, bloco: str | None = None, busca: str | None = None) -> list[Morador]:
    return get_service(request).list(bloco=bloco, busca=busca)


@router.post("", response_model=Morador, status_code=status.HTTP_201_CREATED)
def create_resident(request: Request, data: MoradorInput) -> Morador:
    return get_service(request).create(data)


@router.put("/{item_id}", response_model=Morador)
def update_resident(request: Request, item_id: str, data: MoradorInput) -> Morador:
    return get_service(request).update(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resident(request: Request, item_id: str) -> None:
    get_service(request).delete(item_id)


@router.post("/importar", status_code=status.HTTP_200_OK)
def import_residents(request: Request, batch: MoradorImportBatch) -> dict[str, int]:
    return {"importados": get_service(request).import_batch(batch)}
