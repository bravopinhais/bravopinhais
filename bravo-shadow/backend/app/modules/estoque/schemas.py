from datetime import date
from decimal import Decimal
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class EstoqueInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: str = Field(min_length=1)
    quantidade: Decimal = Field(default=Decimal("1"), ge=0, max_digits=14, decimal_places=3)
    minimo: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=3)
    maximo: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=3)
    etiqueta: str = ""
    fotoNome: str = ""
    fotoCompactadaGzip: str = ""
    marca: str = ""
    linha: str = ""
    fabricante: str = ""
    dataCadastro: str = ""
    setor: str = "Geral / Não definido"
    unidade: str = "un"
    valorUnitario: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    status: Literal["Ativo", "Inativo"] = "Ativo"
    cor: str = ""
    fotoPath: str = ""

    @field_validator(
        "item", "etiqueta", "fotoNome", "marca", "linha", "fabricante",
        "setor", "unidade", "cor", "fotoPath", mode="before",
    )
    @classmethod
    def trim_product_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("dataCadastro", mode="before")
    @classmethod
    def validate_registration_date(cls, value):
        if value is None:
            return ""
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            return ""
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized) is None:
            raise ValueError("A data de cadastro deve estar no formato AAAA-MM-DD.")
        try:
            return date.fromisoformat(normalized).isoformat()
        except ValueError as exc:
            raise ValueError("A data de cadastro deve ser uma data válida.") from exc

    @field_serializer("quantidade", "minimo", "maximo", "valorUnitario", when_used="json")
    def serialize_numeric_fields(self, value: Decimal) -> float:
        return float(value)


class EstoqueItem(EstoqueInput):
    id: str
