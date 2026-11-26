from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FinanceiroInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["Receber", "Pagar"]
    planoContaId: str = ""
    historico: str = Field(min_length=1)
    valor: float


class FinanceiroTitulo(FinanceiroInput):
    id: str
