from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FormaMonetariaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1)
    multaPct: float = Field(default=2.0, ge=0, le=100, allow_inf_nan=False)

    @field_validator("multaPct")
    @classmethod
    def multa_com_ate_duas_casas_decimais(cls, value: float) -> float:
        if Decimal(str(value)).as_tuple().exponent < -2:
            raise ValueError("A multa deve ter no máximo duas casas decimais.")
        return value

    @field_validator("nome")
    @classmethod
    def nome_nao_pode_ser_apenas_espacos(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome da forma monetária é obrigatório.")
        return value


class FormaMonetaria(FormaMonetariaInput):
    id: str
