from fastapi import APIRouter, Request, status
from .schemas import Conselheiro, ConselheiroInput
from .service import ConselheirosService

router = APIRouter(prefix="/api/v1/conselheiros", tags=["Conselheiros"])


def get_service(request: Request) -> ConselheirosService:
    return request.app.state.services.conselheiros


@router.get("", response_model=list[Conselheiro])
def list_council(request: Request) -> list[Conselheiro]:
    return get_service(request).list()


@router.post("", response_model=Conselheiro, status_code=status.HTTP_201_CREATED)
def create_council_member(request: Request, data: ConselheiroInput) -> Conselheiro:
    return get_service(request).create(data)


@router.put("/{item_id}", response_model=Conselheiro)
def update_council_member(request: Request, item_id: str, data: ConselheiroInput) -> Conselheiro:
    return get_service(request).update(item_id, data)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_council_member(request: Request, item_id: str) -> None:
    get_service(request).delete(item_id)
