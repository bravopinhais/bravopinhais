from pydantic import BaseModel, ConfigDict, Field


class FormaMonetariaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1)
    multaPct: float = 0.0


class FormaMonetaria(FormaMonetariaInput):
    id: str
