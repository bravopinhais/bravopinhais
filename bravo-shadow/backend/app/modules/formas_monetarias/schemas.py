from pydantic import BaseModel, ConfigDict, Field, field_validator


class FormaMonetariaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=1, max_length=100)
    multaPct: float = Field(default=2.0, ge=0, le=100)

    @field_validator("nome")
    @classmethod
    def nome_nao_pode_ser_apenas_espacos(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("O nome da forma monetária é obrigatório.")
        return value


class FormaMonetaria(FormaMonetariaInput):
    id: str
