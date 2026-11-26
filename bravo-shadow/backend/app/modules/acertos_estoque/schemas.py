from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AcertoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["Entrada", "Saída"]
    produtoId: str = Field(min_length=1)
    quantidade: int = Field(gt=0)
    motivo: str = Field(min_length=1)
    motivoId: str | None = None


class Acerto(AcertoInput):
    id: str
    data: str
