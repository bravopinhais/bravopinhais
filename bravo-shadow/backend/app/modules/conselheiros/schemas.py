from pydantic import BaseModel, ConfigDict, Field, field_validator

class ConselheiroInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str = Field(min_length=1)
    cargo: str = Field(min_length=1)
    BlocoAp: str = ""
    telefone: str = ""

    @field_validator("*", mode="before")
    @classmethod
    def trim_string_fields(cls, value):
        return value.strip() if isinstance(value, str) else value

class Conselheiro(ConselheiroInput):
    id: str
