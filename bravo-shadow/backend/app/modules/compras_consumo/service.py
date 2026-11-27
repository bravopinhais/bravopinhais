from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from .schemas import (
    ComprasConsumoKpis,
    ComprasConsumoMes,
    ComprasConsumoProduto,
    ComprasConsumoRelatorio,
)

ZERO = Decimal("0")
ONE = Decimal("1")
MONEY = Decimal("0.01")


class ListService(Protocol):
    def list(self) -> list: ...


@dataclass(frozen=True)
class MovementRecord:
    movement: object
    movement_date: date
    month: str


def _as_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            return None


def _decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value if value is not None else 0))
    except Exception:
        return ZERO


def _is_purchase_reason(reason: str) -> bool:
    normalized = reason.casefold()
    return "compra" in normalized or "reposi" in normalized


def _is_loss_reason(reason: str) -> bool:
    normalized = reason.casefold()
    return any(term in normalized for term in ("perda", "avaria", "quebra", "ajuste", "invent"))


def _month_range(start: date | None, end: date | None, observed: list[str]) -> list[str]:
    if start is None or end is None:
        months = sorted(set(observed))
        return months[-12:]
    cursor = date(start.year, start.month, 1)
    last = date(end.year, end.month, 1)
    result: list[str] = []
    while cursor <= last and len(result) < 120:
        result.append(cursor.strftime("%Y-%m"))
        cursor = date(cursor.year + (cursor.month == 12), 1 if cursor.month == 12 else cursor.month + 1, 1)
    return result[-12:]


class ComprasConsumoService:
    """Relatório somente leitura calculado sobre estoque e movimentos da mesma instância."""

    def __init__(self, *, estoque: ListService, acertos_estoque: ListService) -> None:
        self._estoque = estoque
        self._acertos = acertos_estoque

    def report(
        self,
        *,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        setor: str | None = None,
        busca: str | None = None,
        tratar_todas_entradas_como_compras: bool = False,
        incluir_inativos: bool = False,
        ordenar: str = "maior_consumo",
    ) -> ComprasConsumoRelatorio:
        if data_inicio and data_fim and data_inicio > data_fim:
            raise ValueError("A data inicial não pode ser posterior à data final.")

        products = self._estoque.list()
        movements = self._acertos.list()
        product_by_id = {item.id: item for item in products}
        normalized_search = (busca or "").strip().casefold()
        normalized_sector = (setor or "").strip().casefold()

        selected_products = {}
        for product in products:
            status = getattr(product, "status", "Ativo")
            if not incluir_inativos and status != "Ativo":
                continue
            if normalized_sector and normalized_sector != "todos":
                if getattr(product, "setor", "").casefold() != normalized_sector:
                    continue
            searchable = " ".join((
                getattr(product, "item", ""),
                getattr(product, "etiqueta", ""),
                getattr(product, "marca", ""),
            )).casefold()
            if normalized_search and normalized_search not in searchable:
                continue
            selected_products[product.id] = product

        valid_movements: list[MovementRecord] = []
        invalid_dates = 0
        for movement in movements:
            movement_date = _as_date(getattr(movement, "data", None))
            if movement_date is None:
                invalid_dates += 1
                continue
            if data_inicio and movement_date < data_inicio:
                continue
            if data_fim and movement_date > data_fim:
                continue
            if movement.produtoId not in selected_products:
                continue
            valid_movements.append(MovementRecord(
                movement=movement,
                movement_date=movement_date,
                month=movement_date.strftime("%Y-%m"),
            ))

        buckets: dict[str, dict] = defaultdict(lambda: {
            "compras": ZERO, "outras": ZERO, "consumo": ZERO, "perdas": ZERO,
            "valor_comprado": ZERO, "valor_consumido": ZERO, "meses": set(),
        })
        monthly: dict[str, dict] = defaultdict(lambda: {
            "quantidade_comprada": ZERO, "quantidade_consumida": ZERO,
            "valor_comprado": ZERO, "valor_consumido": ZERO,
        })

        for record in valid_movements:
            movement = record.movement
            product = selected_products[movement.produtoId]
            quantity = _decimal(movement.quantidade)
            reason = str(getattr(movement, "motivo", "") or "")
            movement_type = str(getattr(movement, "tipo", "") or "").casefold()
            bucket = buckets[movement.produtoId]
            bucket["meses"].add(record.month)
            if movement_type.startswith("entr"):
                is_purchase = tratar_todas_entradas_como_compras or _is_purchase_reason(reason)
                if is_purchase:
                    bucket["compras"] += quantity
                    monthly[record.month]["quantidade_comprada"] += quantity
                    value = quantity * _decimal(getattr(product, "valorUnitario", 0))
                    bucket["valor_comprado"] += value
                    monthly[record.month]["valor_comprado"] += value
                else:
                    bucket["outras"] += quantity
            else:
                if _is_loss_reason(reason):
                    bucket["perdas"] += quantity
                else:
                    bucket["consumo"] += quantity
                    monthly[record.month]["quantidade_consumida"] += quantity
                    value = quantity * _decimal(getattr(product, "valorUnitario", 0))
                    bucket["valor_consumido"] += value
                    monthly[record.month]["valor_consumido"] += value

        period_months = _month_range(data_inicio, data_fim, [m.month for m in valid_movements])
        month_count = max(len(period_months), 1)
        rows: list[ComprasConsumoProduto] = []
        for product_id, product in selected_products.items():
            values = buckets[product_id]
            stock = _decimal(product.quantidade)
            minimum = _decimal(getattr(product, "minimo", 0))
            maximum = _decimal(getattr(product, "maximo", 0))
            average = values["consumo"] / Decimal(month_count)
            coverage = stock / average if average > ZERO else None
            if not values["meses"]:
                situation = "Sem movimentação"
            elif stock <= ZERO:
                situation = "Repor"
            elif stock <= minimum:
                situation = "Repor"
            elif coverage is not None and coverage < ONE:
                situation = "Cobertura baixa"
            elif values["consumo"] == ZERO and values["compras"] > ZERO:
                situation = "Comprado sem consumo"
            elif values["consumo"] == ZERO:
                situation = "Sem consumo"
            elif values["compras"] > values["consumo"] * Decimal("1.5") and maximum > ZERO and stock > maximum:
                situation = "Comprando acima do uso"
            else:
                situation = "Equilibrado"
            rows.append(ComprasConsumoProduto(
                produtoId=product_id,
                produto=product.item,
                etiqueta=getattr(product, "etiqueta", ""),
                marca=getattr(product, "marca", ""),
                setor=getattr(product, "setor", "Geral / Não definido"),
                unidade=getattr(product, "unidade", "un"),
                compras=values["compras"],
                outrasEntradas=values["outras"],
                consumo=values["consumo"],
                perdasAjustes=values["perdas"],
                diferenca=values["compras"] - values["consumo"],
                estoqueAtual=stock,
                mediaMensal=average,
                coberturaMeses=coverage,
                valorComprado=values["valor_comprado"].quantize(MONEY),
                valorConsumido=values["valor_consumido"].quantize(MONEY),
                situacao=situation,
            ))

        ordering = {
            "maior_consumo": lambda row: (-row.consumo, row.produto.casefold()),
            "maior_compra": lambda row: (-row.compras, row.produto.casefold()),
            "diferenca": lambda row: (-row.diferenca, row.produto.casefold()),
            "menor_cobertura": lambda row: (
                row.coberturaMeses is None,
                row.coberturaMeses if row.coberturaMeses is not None else ZERO,
                row.produto.casefold(),
            ),
            "nome": lambda row: row.produto.casefold(),
        }
        rows.sort(key=ordering.get(ordenar, ordering["maior_consumo"]))

        units = {row.unidade for row in rows if row.compras or row.consumo or row.perdasAjustes}
        compatible = len(units) <= 1
        unit = next(iter(units)) if len(units) == 1 else None
        month_rows = [
            ComprasConsumoMes(
                mes=month,
                quantidadeComprada=monthly[month]["quantidade_comprada"],
                quantidadeConsumida=monthly[month]["quantidade_consumida"],
                valorComprado=monthly[month]["valor_comprado"].quantize(MONEY),
                valorConsumido=monthly[month]["valor_consumido"].quantize(MONEY),
            )
            for month in period_months
        ]

        return ComprasConsumoRelatorio(
            dataInicio=data_inicio.isoformat() if data_inicio else None,
            dataFim=data_fim.isoformat() if data_fim else None,
            setor=setor or "Todos",
            busca=busca or "",
            tratarTodasEntradasComoCompras=tratar_todas_entradas_como_compras,
            unidadesCompativeis=compatible,
            unidadeConsolidada=unit,
            movimentosSemDataValida=invalid_dates,
            kpis=ComprasConsumoKpis(
                compras=sum((row.compras for row in rows), ZERO),
                consumo=sum((row.consumo for row in rows), ZERO),
                perdasAjustes=sum((row.perdasAjustes for row in rows), ZERO),
                produtosEmAlerta=sum(row.situacao in {"Repor", "Cobertura baixa", "Comprando acima do uso"} for row in rows),
                valorComprado=sum((row.valorComprado for row in rows), ZERO).quantize(MONEY),
                valorConsumido=sum((row.valorConsumido for row in rows), ZERO).quantize(MONEY),
            ),
            evolucaoMensal=month_rows,
            produtos=rows,
        )
