from pydantic import BaseModel, ConfigDict, Field

class FornecedorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cnpj: str = Field(min_length=1)
    razaoSocial: str = Field(min_length=1)

class Fornecedor(FornecedorInput):
    id: str
