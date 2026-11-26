from pydantic import BaseModel, ConfigDict, Field

class DocumentoInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pasta: str = 'Geral'
    titulo: str = Field(min_length=1)
    nomeArquivo: str = Field(min_length=1)
    arquivoCompactadoGzip: str = Field(min_length=1)

class Documento(DocumentoInput):
    id: str
