from pydantic import BaseModel, ConfigDict, Field

class MotivoAcertoInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    nome: str = Field(min_length=1)

class MotivoAcerto(MotivoAcertoInput):
    id: str
