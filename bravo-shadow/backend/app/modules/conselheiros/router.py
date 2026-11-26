from fastapi import APIRouter, status
from .schemas import Conselheiro, ConselheiroInput
from .service import conselheiros_service

router = APIRouter(prefix="/api/v1/conselheiros", tags=["Conselheiros"])

@router.get("", response_model=list[Conselheiro])
def list_council() -> list[Conselheiro]:
    return conselheiros_service.list()

@router.post("", response_model=Conselheiro, status_code=status.HTTP_201_CREATED)
def create_council_member(data: ConselheiroInput) -> Conselheiro:
    return conselheiros_service.create(data)

@router.put("/{item_id}", response_model=Conselheiro)
def update_council_member(item_id: str, data: ConselheiroInput) -> Conselheiro:
    return conselheiros_service.update(item_id, data)

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_council_member(item_id: str) -> None:
    conselheiros_service.delete(item_id)
