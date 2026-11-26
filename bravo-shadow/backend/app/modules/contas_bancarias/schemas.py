from pydantic import BaseModel, ConfigDict, Field


class ContaBancariaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    banco: str = Field(min_length=1)
    saldo: float = 0.0


class ContaBancaria(ContaBancariaInput):
    id: str
