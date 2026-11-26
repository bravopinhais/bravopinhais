from pydantic import BaseModel, ConfigDict, Field

class ConselheiroInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str = Field(min_length=1)
    cargo: str = Field(min_length=1)
    BlocoAp: str = ""
    telefone: str = ""

class Conselheiro(ConselheiroInput):
    id: str
