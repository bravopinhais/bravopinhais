from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FinanceiroInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["Receber", "Pagar"]
    planoContaId: str = ""
    historico: str = Field(min_length=1)
    valor: Decimal = Field(max_digits=14, decimal_places=2)


class FinanceiroTitulo(FinanceiroInput):
    id: str
    version: int = Field(default=1, ge=1)
