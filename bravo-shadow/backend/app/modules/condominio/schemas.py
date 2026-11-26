from pydantic import BaseModel, ConfigDict

class CondominioPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nome: str | None = None
    cnpj: str | None = None
    razaoSocial: str | None = None
    endereco: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    uf: str | None = None
    cep: str | None = None
    telefone: str | None = None
    email: str | None = None
    copelBloco1: str | None = None
    copelBloco2: str | None = None
    copelBloco3: str | None = None
    copelBloco4: str | None = None
    copelAreasComuns: str | None = None
    gasSalao: str | None = None
    sanepar: str | None = None

class Condominio(CondominioPatch):
    pass
