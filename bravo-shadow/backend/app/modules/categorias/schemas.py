from pydantic import BaseModel, ConfigDict, Field, field_validator

class CategoriaInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nome: str = Field(min_length=1)

    @field_validator("nome", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value

class Categoria(CategoriaInput):
    id: str
