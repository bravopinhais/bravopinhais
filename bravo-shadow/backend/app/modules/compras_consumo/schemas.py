from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class ComprasConsumoProduto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    produtoId: str
    produto: str
    etiqueta: str
    marca: str
    setor: str
    unidade: str
    compras: Decimal
    outrasEntradas: Decimal
    consumo: Decimal
    perdasAjustes: Decimal
    diferenca: Decimal
    estoqueAtual: Decimal
    mediaMensal: Decimal
    coberturaMeses: Decimal | None
    valorComprado: Decimal
    valorConsumido: Decimal
    situacao: str


class ComprasConsumoKpis(BaseModel):
    compras: Decimal
    consumo: Decimal
    perdasAjustes: Decimal
    produtosEmAlerta: int
    valorComprado: Decimal
    valorConsumido: Decimal


class ComprasConsumoMes(BaseModel):
    mes: str
    quantidadeComprada: Decimal
    quantidadeConsumida: Decimal
    valorComprado: Decimal
    valorConsumido: Decimal


class ComprasConsumoRelatorio(BaseModel):
    dataInicio: str | None
    dataFim: str | None
    setor: str
    busca: str
    tratarTodasEntradasComoCompras: bool
    unidadesCompativeis: bool
    unidadeConsolidada: str | None
    movimentosSemDataValida: int
    kpis: ComprasConsumoKpis
    evolucaoMensal: list[ComprasConsumoMes]
    produtos: list[ComprasConsumoProduto]
