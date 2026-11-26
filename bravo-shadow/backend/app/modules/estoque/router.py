from fastapi import APIRouter, Request, status

from .schemas import EstoqueInput, EstoqueItem
from .service import EstoqueService

router = APIRouter(prefix="/api/v1/estoque", tags=["Estoque e Inventário"])


def get_service(request: Request) -> EstoqueService:
    return request.app.state.services.estoque


@router.get("", response_model=list[EstoqueItem])
def list_items(request: Request):
    return get_service(request).list()


@router.post("", response_model=EstoqueItem, status_code=status.HTTP_201_CREATED)
def create_item(data: EstoqueInput, request: Request):
    return get_service(request).create(data)


@router.put("/{item_id}", response_model=EstoqueItem)
def update_item(item_id: str, data: EstoqueInput, request: Request):
    return get_service(request).update(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: str, request: Request):
    get_service(request).delete(item_id)
