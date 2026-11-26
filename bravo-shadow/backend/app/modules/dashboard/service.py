from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


class ListService(Protocol):
    def list(self) -> list: ...


@dataclass(frozen=True)
class DashboardSummary:
    """Resumo agregado de leitura exposto pelo endpoint protegido do Dashboard."""

    total_formas_monetarias: int
    total_contas_plano: int
    total_titulos_financeiros: int
    total_produtos_estoque: int
    total_moradores: int
    total_fornecedores: int
    total_empregados: int
    total_documentos: int
    total_titulos_receber: int
    total_titulos_pagar: int
    valor_receber: Decimal
    valor_pagar: Decimal
    diferenca_titulos: Decimal


class DashboardService:
    """Calcula indicadores estritamente a partir dos serviços da mesma instância."""

    def __init__(
        self,
        *,
        formas_monetarias: ListService,
        plano_contas: ListService,
        financeiro: ListService,
        estoque: ListService,
        moradores: ListService,
        fornecedores: ListService,
        empregados: ListService,
        documentos: ListService,
    ) -> None:
        self._formas_monetarias = formas_monetarias
        self._plano_contas = plano_contas
        self._financeiro = financeiro
        self._estoque = estoque
        self._moradores = moradores
        self._fornecedores = fornecedores
        self._empregados = empregados
        self._documentos = documentos

    def summary(self) -> DashboardSummary:
        # Uma leitura por serviço; nenhum dado pessoal ou texto de histórico é retornado.
        formas = self._formas_monetarias.list()
        contas = self._plano_contas.list()
        titulos = self._financeiro.list()
        produtos = self._estoque.list()
        moradores = self._moradores.list()
        fornecedores = self._fornecedores.list()
        empregados = self._empregados.list()
        documentos = self._documentos.list()

        receber = [item for item in titulos if item.tipo == "Receber"]
        pagar = [item for item in titulos if item.tipo == "Pagar"]
        valor_receber = sum((item.valor for item in receber), Decimal("0.00"))
        valor_pagar = sum((item.valor for item in pagar), Decimal("0.00"))

        return DashboardSummary(
            total_formas_monetarias=len(formas),
            total_contas_plano=len(contas),
            total_titulos_financeiros=len(titulos),
            total_produtos_estoque=len(produtos),
            total_moradores=len(moradores),
            total_fornecedores=len(fornecedores),
            total_empregados=len(empregados),
            total_documentos=len(documentos),
            total_titulos_receber=len(receber),
            total_titulos_pagar=len(pagar),
            valor_receber=valor_receber,
            valor_pagar=valor_pagar,
            diferenca_titulos=valor_receber - valor_pagar,
        )
