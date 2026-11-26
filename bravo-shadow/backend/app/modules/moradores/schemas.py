from pydantic import BaseModel, ConfigDict, Field

class MoradorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bloco: str = Field(min_length=1)
    apartamento: str = Field(min_length=1)
    nome: str = Field(min_length=1)
    email: str = ""
    telefone: str = ""
    cpf: str = ""
    petNome: str = ""
    vagaGaragem: str = ""

class Morador(MoradorInput):
    id: str

class MoradorImport(MoradorInput):
    bloco: str = "1"
    nome: str = "Sem Nome"

class MoradorImportBatch(BaseModel):
    moradores: list[MoradorImport] = Field(default_factory=list)
