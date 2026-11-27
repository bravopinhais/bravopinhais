from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.authorization import require_capability_dependency
from .schemas import ComprasConsumoRelatorio
from .service import ComprasConsumoService

router = APIRouter(prefix="/api/v1/compras-consumo", tags=["Compras x Consumo"])


def get_service(request: Request) -> ComprasConsumoService:
    return request.app.state.compras_consumo_service


@router.get(
    "",
    response_model=ComprasConsumoRelatorio,
    dependencies=[Depends(require_capability_dependency("relatorios:read"))],
)
def read_report(
    request: Request,
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    setor: str | None = Query(default=None, max_length=120),
    busca: str | None = Query(default=None, max_length=160),
    tratar_todas_entradas_como_compras: bool = Query(default=False),
    incluir_inativos: bool = Query(default=False),
    ordenar: str = Query(default="maior_consumo", pattern="^(maior_consumo|maior_compra|diferenca|menor_cobertura|nome)$"),
):
    try:
        return get_service(request).report(
            data_inicio=data_inicio,
            data_fim=data_fim,
            setor=setor,
            busca=busca,
            tratar_todas_entradas_como_compras=tratar_todas_entradas_como_compras,
            incluir_inativos=incluir_inativos,
            ordenar=ordenar,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
