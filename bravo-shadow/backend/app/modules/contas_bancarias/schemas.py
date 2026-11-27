from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class ContaBancariaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    banco: str = Field(min_length=1)
    saldo: Decimal = Field(default=Decimal("0.00"), max_digits=14, decimal_places=2, allow_inf_nan=False)

    @field_validator("banco")
    @classmethod
    def normalize_bank_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("O nome do banco não pode ficar vazio.")
        return normalized

    @field_serializer("saldo", when_used="json")
    def serialize_saldo(self, value: Decimal) -> float:
        # Mantém o contrato JSON numérico legado; o cálculo interno usa Decimal.
        return float(value)


class ContaBancaria(ContaBancariaInput):
    id: str
