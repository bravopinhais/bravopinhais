from pydantic import BaseModel, ConfigDict, Field, field_validator

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

    @field_validator("*", mode="before")
    @classmethod
    def trim_string_fields(cls, value):
        # Normaliza espaços sem alterar pontuação ou formato legado de CPF/telefone.
        return value.strip() if isinstance(value, str) else value

class Morador(MoradorInput):
    id: str

class MoradorImport(MoradorInput):
    bloco: str = "1"
    nome: str = "Sem Nome"

class MoradorImportBatch(BaseModel):
    moradores: list[MoradorImport] = Field(default_factory=list)


class MoradorResumo(BaseModel):
    """Campos mínimos para a tabela; documentos e contatos ficam fora da listagem."""
    id: str
    bloco: str
    apartamento: str
    nome: str
