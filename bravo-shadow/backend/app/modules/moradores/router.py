from fastapi import APIRouter, Query, status
from .schemas import Morador, MoradorInput, MoradorImportBatch
from .service import moradores_service

router = APIRouter(prefix="/api/v1/moradores", tags=["Moradores"])

@router.get("", response_model=list[Morador])
def list_residents(bloco: str | None = None, busca: str | None = None) -> list[Morador]:
    return moradores_service.list(bloco=bloco, busca=busca)

@router.post("", response_model=Morador, status_code=status.HTTP_201_CREATED)
def create_resident(data: MoradorInput) -> Morador:
    return moradores_service.create(data)

@router.put("/{item_id}", response_model=Morador)
def update_resident(item_id: str, data: MoradorInput) -> Morador:
    return moradores_service.update(item_id, data)

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resident(item_id: str) -> None:
    moradores_service.delete(item_id)

@router.post("/importar", status_code=status.HTTP_200_OK)
def import_residents(batch: MoradorImportBatch) -> dict[str, int]:
    return {"importados": moradores_service.import_batch(batch)}
