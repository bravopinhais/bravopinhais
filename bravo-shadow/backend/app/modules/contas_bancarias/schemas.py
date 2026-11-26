from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ContaBancariaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    banco: str = Field(min_length=1)
    saldo: Decimal = Field(default=Decimal("0.00"), max_digits=14, decimal_places=2)

    @field_serializer("saldo", when_used="json")
    def serialize_saldo(self, value: Decimal) -> float:
        # Mantém o contrato JSON numérico legado; o cálculo interno usa Decimal.
        return float(value)


class ContaBancaria(ContaBancariaInput):
    id: str
