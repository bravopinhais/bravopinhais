from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.modules.compras_consumo.service import ComprasConsumoService


class ListSource:
    def __init__(self, items):
        self.items = items

    def list(self):
        return list(self.items)


def product(**overrides):
    values = {
        "id": "p1",
        "item": "Detergente",
        "etiqueta": "ETQ-1",
        "marca": "Marca A",
        "setor": "DML",
        "unidade": "l",
        "valorUnitario": Decimal("8.50"),
        "quantidade": Decimal("3.000"),
        "minimo": Decimal("1.000"),
        "maximo": Decimal("10.000"),
        "status": "Ativo",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def movement(tipo, quantidade, motivo, data="2026-11-05", produto_id="p1"):
    return SimpleNamespace(
        id=f"m-{tipo}-{motivo}-{quantidade}",
        tipo=tipo,
        quantidade=Decimal(str(quantidade)),
        motivo=motivo,
        data=data,
        produtoId=produto_id,
    )


def service(products, movements):
    return ComprasConsumoService(
        estoque=ListSource(products),
        acertos_estoque=ListSource(movements),
    )


def test_report_classifies_fractional_purchases_consumption_and_losses():
    report = service(
        [product()],
        [
            movement("Entrada", "2.500", "Compra mensal"),
            movement("Entrada", "0.250", "Devolução"),
            movement("Saída", "0.750", "Consumo cozinha"),
            movement("Saída", "0.125", "Avaria"),
        ],
    ).report(data_inicio=date(2026, 11, 1), data_fim=date(2026, 11, 30))

    row = report.produtos[0]
    assert row.compras == Decimal("2.500")
    assert row.outrasEntradas == Decimal("0.250")
    assert row.consumo == Decimal("0.750")
    assert row.perdasAjustes == Decimal("0.125")
    assert row.diferenca == Decimal("1.750")
    assert row.valorComprado == Decimal("21.25")
    assert row.valorConsumido == Decimal("6.38")
    assert report.kpis.produtosEmAlerta == 0


def test_report_can_treat_all_entries_as_purchases_and_filters_products():
    report = service(
        [product(), product(id="p2", item="Sabão", setor="Lavanderia")],
        [
            movement("Entrada", "1.000", "Transferência"),
            movement("Entrada", "4.000", "Compra", produto_id="p2"),
        ],
    ).report(
        setor="DML",
        tratar_todas_entradas_como_compras=True,
    )

    assert len(report.produtos) == 1
    assert report.produtos[0].compras == Decimal("1.000")
    assert report.produtos[0].outrasEntradas == Decimal("0")


def test_report_does_not_combine_quantities_with_different_units():
    report = service(
        [product(), product(id="p2", item="Sabão", unidade="kg")],
        [
            movement("Entrada", "1.000", "Compra", produto_id="p1"),
            movement("Entrada", "2.000", "Compra", produto_id="p2"),
        ],
    ).report()

    assert report.unidadesCompativeis is False
    assert report.unidadeConsolidada is None
    assert all(row.quantidadeComprada == 0 for row in report.evolucaoMensal)


def test_report_ignores_invalid_dates_and_can_include_inactive_products():
    report = service(
        [product(status="Inativo")],
        [movement("Saída", "1.000", "Consumo", data="data-invalida")],
    ).report(incluir_inativos=True)

    assert report.movimentosSemDataValida == 1
    assert len(report.produtos) == 1
    assert report.produtos[0].situacao == "Sem movimentação"


def test_report_rejects_reversed_date_range():
    import pytest

    with pytest.raises(ValueError):
        service([product()], []).report(
            data_inicio=date(2026, 11, 30),
            data_fim=date(2026, 11, 1),
        )


def test_monthly_evolution_returns_latest_twelve_months_for_long_history():
    report = service(
        [product()],
        [movement("Entrada", "1.000", "Compra", data="2026-11-05")],
    ).report(
        data_inicio=date(2000, 1, 1),
        data_fim=date(2026, 11, 30),
    )

    months = [row.mes for row in report.evolucaoMensal]
    assert len(months) == 12
    assert months[0] == "2025-12"
    assert months[-1] == "2026-11"


def test_monthly_evolution_handles_reversed_observed_window_without_dates():
    report = service(
        [product()],
        [],
    ).report()

    assert report.evolucaoMensal == []
