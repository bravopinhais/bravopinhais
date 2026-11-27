import csv
from datetime import date
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from app.core.authorization import require_capability_dependency
from .schemas import ComprasConsumoRelatorio
from .service import ComprasConsumoService

router = APIRouter(prefix="/api/v1/compras-consumo", tags=["Compras x Consumo"])


def get_service(request: Request) -> ComprasConsumoService:
    return request.app.state.compras_consumo_service


def build_report(
    request: Request,
    data_inicio: date | None,
    data_fim: date | None,
    setor: str | None,
    busca: str | None,
    tratar_todas_entradas_como_compras: bool,
    incluir_inativos: bool,
    ordenar: str,
) -> ComprasConsumoRelatorio:
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
    return build_report(
        request, data_inicio, data_fim, setor, busca,
        tratar_todas_entradas_como_compras, incluir_inativos, ordenar,
    )


@router.get(
    "/export.csv",
    dependencies=[Depends(require_capability_dependency("relatorios:read"))],
)
def export_report_csv(
    request: Request,
    data_inicio: date | None = Query(default=None),
    data_fim: date | None = Query(default=None),
    setor: str | None = Query(default=None, max_length=120),
    busca: str | None = Query(default=None, max_length=160),
    tratar_todas_entradas_como_compras: bool = Query(default=False),
    incluir_inativos: bool = Query(default=False),
    ordenar: str = Query(default="maior_consumo", pattern="^(maior_consumo|maior_compra|diferenca|menor_cobertura|nome)$"),
):
    report = build_report(
        request, data_inicio, data_fim, setor, busca,
        tratar_todas_entradas_como_compras, incluir_inativos, ordenar,
    )
    output = StringIO(newline="")
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Código", "Produto", "Marca", "Setor", "Unidade", "Compras",
        "Outras entradas", "Consumo", "Perdas/ajustes", "Diferença",
        "Estoque atual", "Média mensal", "Cobertura (meses)",
        "Valor comprado (R$)", "Valor consumido (R$)", "Situação",
    ])
    def safe_text(value: str) -> str:
        text = str(value or "")
        return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text

    for row in report.produtos:
        writer.writerow([
            safe_text(row.etiqueta), safe_text(row.produto), safe_text(row.marca),
            safe_text(row.setor), safe_text(row.unidade),
            str(row.compras), str(row.outrasEntradas), str(row.consumo),
            str(row.perdasAjustes), str(row.diferenca), str(row.estoqueAtual),
            str(row.mediaMensal),
            "" if row.coberturaMeses is None else str(row.coberturaMeses),
            str(row.valorComprado), str(row.valorConsumido), safe_text(row.situacao),
        ])
    csv_content = "\ufeff" + output.getvalue()
    filename = "compras-consumo.csv"
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
