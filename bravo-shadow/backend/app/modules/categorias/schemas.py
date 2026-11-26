from pydantic import BaseModel, ConfigDict, Field

class CategoriaInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nome: str = Field(min_length=1)

class Categoria(CategoriaInput):
    id: str
