from fastapi import APIRouter, status

from .schemas import FormaMonetaria, FormaMonetariaInput
from .service import formas_monetarias_service

router = APIRouter(prefix="/api/v1/formas-monetarias", tags=["Formas Monetárias"])


@router.get("", response_model=list[FormaMonetaria])
def list_forms() -> list[FormaMonetaria]:
    return formas_monetarias_service.list()


@router.post("", response_model=FormaMonetaria, status_code=status.HTTP_201_CREATED)
def create_form(data: FormaMonetariaInput) -> FormaMonetaria:
    return formas_monetarias_service.create(data)


@router.put("/{item_id}", response_model=FormaMonetaria)
def update_form(item_id: str, data: FormaMonetariaInput) -> FormaMonetaria:
    return formas_monetarias_service.update(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_form(item_id: str) -> None:
    formas_monetarias_service.delete(item_id)
