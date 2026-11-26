from decimal import Decimal
from types import SimpleNamespace

from app.modules.dashboard.service import DashboardService


class FakeListService:
    def __init__(self, items):
        self.items = items

    def list(self):
        return list(self.items)


def make_service(**overrides):
    defaults = {
        "formas_monetarias": [],
        "plano_contas": [],
        "financeiro": [],
        "estoque": [],
        "moradores": [],
        "fornecedores": [],
        "empregados": [],
        "documentos": [],
    }
    defaults.update(overrides)
    return DashboardService(**{
        name: FakeListService(items) for name, items in defaults.items()
    })


def test_dashboard_summary_returns_zero_counts_for_empty_shadow():
    summary = make_service().summary()

    assert summary.total_titulos_financeiros == 0
    assert summary.valor_receber == Decimal("0.00")
    assert summary.valor_pagar == Decimal("0.00")
    assert summary.diferenca_titulos == Decimal("0.00")


def test_dashboard_summary_aggregates_receivable_and_payable_without_float():
    financeiro = [
        SimpleNamespace(tipo="Receber", valor=Decimal("120.10")),
        SimpleNamespace(tipo="Receber", valor=Decimal("9.90")),
        SimpleNamespace(tipo="Pagar", valor=Decimal("30.25")),
    ]

    summary = make_service(financeiro=financeiro).summary()

    assert summary.total_titulos_financeiros == 3
    assert summary.total_titulos_receber == 2
    assert summary.total_titulos_pagar == 1
    assert summary.valor_receber == Decimal("130.00")
    assert summary.valor_pagar == Decimal("30.25")
    assert summary.diferenca_titulos == Decimal("99.75")


def test_dashboard_summary_does_not_expose_personal_or_historic_fields():
    moradores = [SimpleNamespace(nome="Nome privado", apartamento="101")]
    financeiro = [
        SimpleNamespace(
            tipo="Receber",
            valor=Decimal("10.00"),
            historico="Descrição privada",
        )
    ]

    summary = make_service(moradores=moradores, financeiro=financeiro).summary()

    assert summary.total_moradores == 1
    assert not hasattr(summary, "moradores")
    assert not hasattr(summary, "historicos")
