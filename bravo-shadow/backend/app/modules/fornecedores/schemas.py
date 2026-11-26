from pydantic import BaseModel, ConfigDict, Field, field_validator

class FornecedorInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cnpj: str = Field(min_length=1)
    razaoSocial: str = Field(min_length=1)

    @field_validator("cnpj", "razaoSocial", mode="before")
    @classmethod
    def trim_required_fields(cls, value):
        return value.strip() if isinstance(value, str) else value

class Fornecedor(FornecedorInput):
    id: str
