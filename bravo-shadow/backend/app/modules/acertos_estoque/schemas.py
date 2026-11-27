from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class AcertoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: Literal["Entrada", "Saída"]
    produtoId: str = Field(min_length=1)
    quantidade: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    motivo: str = Field(min_length=1)
    motivoId: str | None = None

    @field_validator("produtoId", "motivo", mode="before")
    @classmethod
    def trim_required_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("motivoId", mode="before")
    @classmethod
    def normalize_reason_id(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value

    @field_serializer("quantidade", when_used="json")
    def serialize_quantity(self, value: Decimal) -> float:
        return float(value)


class Acerto(AcertoInput):
    id: str
    data: str
