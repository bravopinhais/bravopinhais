from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from app.modules.relatorios.schemas import DREContaLinha, DREResumo


CENT = Decimal("0.01")
ZERO = Decimal("0.00")


class RelatoriosService:
    """Agregações gerenciais somente de leitura sobre os serviços existentes."""

    def __init__(self, *, financeiro, plano_contas) -> None:
        self._financeiro = financeiro
        self._plano_contas = plano_contas

    def dre(self) -> DREResumo:
        titulos = self._financeiro.list()
        contas = {conta.id: conta for conta in self._plano_contas.list()}

        totais = {
            "Receber": {"quantidade": 0, "valor": ZERO, "sem_conta_qtd": 0, "sem_conta_valor": ZERO},
            "Pagar": {"quantidade": 0, "valor": ZERO, "sem_conta_qtd": 0, "sem_conta_valor": ZERO},
        }
        agrupados: dict[str, dict[str, dict[str, object]]] = {
            "Receber": {},
            "Pagar": {},
        }

        for titulo in titulos:
            tipo = titulo.tipo
            if tipo not in totais:
                continue
            valor = Decimal(titulo.valor).quantize(CENT)
            total = totais[tipo]
            total["quantidade"] += 1
            total["valor"] += valor

            conta_id = (titulo.planoContaId or "").strip()
            conta = contas.get(conta_id)
            if not conta:
                total["sem_conta_qtd"] += 1
                total["sem_conta_valor"] += valor
                continue

            linha = agrupados[tipo].setdefault(
                conta.id,
                {"codigo": conta.codigo, "nome": conta.nome, "tipo_conta": conta.tipo,
                 "quantidade": 0, "valor": ZERO},
            )
            linha["quantidade"] += 1
            linha["valor"] += valor

        def build_lines(tipo: str) -> list[DREContaLinha]:
            base = totais[tipo]["valor"]
            result = []
            for item in sorted(agrupados[tipo].values(), key=lambda row: (row["codigo"], row["nome"])):
                valor = item["valor"]
                percentual = (valor * Decimal("100") / base).quantize(CENT, rounding=ROUND_HALF_UP) if base else ZERO
                result.append(DREContaLinha(
                    codigo=item["codigo"], nome=item["nome"], tipo_conta=item["tipo_conta"],
                    quantidade_titulos=item["quantidade"], valor=valor, participacao_pct=percentual,
                ))
            return result

        receber = totais["Receber"]
        pagar = totais["Pagar"]
        valor_receber = receber["valor"]
        valor_pagar = pagar["valor"]
        return DREResumo(
            criterio="Todos os títulos cadastrados; sem filtro de período ou status de liquidação.",
            atualizado_em=datetime.now(timezone.utc),
            total_titulos_receber=receber["quantidade"],
            total_titulos_pagar=pagar["quantidade"],
            valor_receber=valor_receber,
            valor_pagar=valor_pagar,
            diferenca_titulos=valor_receber - valor_pagar,
            titulos_receber_sem_conta=receber["sem_conta_qtd"],
            titulos_pagar_sem_conta=pagar["sem_conta_qtd"],
            valor_receber_sem_conta=receber["sem_conta_valor"],
            valor_pagar_sem_conta=pagar["sem_conta_valor"],
            receitas=build_lines("Receber"),
            despesas=build_lines("Pagar"),
        )
