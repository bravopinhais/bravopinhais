from fastapi import APIRouter, Request, status

from .schemas import FormaMonetaria, FormaMonetariaInput
from .service import FormasMonetariasService

router = APIRouter(prefix="/api/v1/formas-monetarias", tags=["Formas Monetárias"])


def get_service(request: Request) -> FormasMonetariasService:
    return request.app.state.services.formas_monetarias


@router.get("", response_model=list[FormaMonetaria])
def list_forms(request: Request) -> list[FormaMonetaria]:
    return get_service(request).list()


@router.post("", response_model=FormaMonetaria, status_code=status.HTTP_201_CREATED)
def create_form(data: FormaMonetariaInput, request: Request) -> FormaMonetaria:
    return get_service(request).create(data)


@router.put("/{item_id}", response_model=FormaMonetaria)
def update_form(item_id: str, data: FormaMonetariaInput, request: Request) -> FormaMonetaria:
    return get_service(request).update(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_form(item_id: str, request: Request) -> None:
    get_service(request).delete(item_id)
