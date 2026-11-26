from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlanoContaInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    codigo: str = Field(min_length=1, max_length=30)
    nome: str = Field(min_length=2, max_length=160)
    tipo: Literal["Receita", "Despesa"]

    @field_validator("codigo", "nome")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("O campo não pode ficar vazio.")
        return value


class PlanoConta(PlanoContaInput):
    id: str
    version: int = Field(default=1, ge=1)
