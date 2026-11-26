from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class FinanceiroInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["Receber", "Pagar"]
    planoContaId: str = ""
    historico: str = Field(min_length=1)
    valor: Decimal = Field(max_digits=14, decimal_places=2)

    @field_validator("historico")
    @classmethod
    def normalize_historico(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("O histórico não pode ficar vazio.")
        return normalized

    @field_validator("planoContaId")
    @classmethod
    def normalize_plano_conta_id(cls, value: str) -> str:
        return value.strip()

    @field_serializer("valor", when_used="json")
    def serialize_valor(self, value: Decimal) -> float:
        # Mantém Decimal internamente e preserva o contrato JSON numérico do legado.
        return float(value)


class FinanceiroTitulo(FinanceiroInput):
    id: str
    version: int = Field(default=1, ge=1)
