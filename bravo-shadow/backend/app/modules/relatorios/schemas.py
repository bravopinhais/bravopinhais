from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer


class DREContaLinha(BaseModel):
    model_config = ConfigDict(frozen=True)

    codigo: str
    nome: str
    tipo_conta: str
    quantidade_titulos: int
    valor: Decimal
    participacao_pct: Decimal

    @field_serializer("valor", "participacao_pct", when_used="json")
    def serialize_decimal(self, value: Decimal) -> float:
        return float(value)


class DREResumo(BaseModel):
    model_config = ConfigDict(frozen=True)

    criterio: str
    atualizado_em: datetime
    total_titulos_receber: int
    total_titulos_pagar: int
    valor_receber: Decimal
    valor_pagar: Decimal
    diferenca_titulos: Decimal
    titulos_receber_sem_conta: int
    titulos_pagar_sem_conta: int
    valor_receber_sem_conta: Decimal
    valor_pagar_sem_conta: Decimal
    receitas: list[DREContaLinha]
    despesas: list[DREContaLinha]

    @field_serializer(
        "valor_receber", "valor_pagar", "diferenca_titulos",
        "valor_receber_sem_conta", "valor_pagar_sem_conta",
        when_used="json",
    )
    def serialize_decimal(self, value: Decimal) -> float:
        return float(value)
