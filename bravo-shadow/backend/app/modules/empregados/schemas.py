from pydantic import BaseModel, ConfigDict, Field

class EmpregadoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str = Field(min_length=1)
    cargo: str = Field(min_length=1)
    empresa: str = ""
    endereco: str = ""
    telefone: str = ""
    contatoEmergenciaNome: str = ""
    contatoEmergenciaTel: str = ""

class Empregado(EmpregadoInput):
    id: str
