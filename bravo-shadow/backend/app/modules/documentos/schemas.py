from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pasta: str = "Geral"
    categoriaId: str | None = None
    titulo: str = Field(min_length=1)
    nomeArquivo: str = Field(min_length=1)
    arquivoCompactadoGzip: str = Field(min_length=1)

    @field_validator("pasta", "titulo", "nomeArquivo", mode="before")
    @classmethod
    def trim_text_metadata(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("categoriaId", mode="before")
    @classmethod
    def normalize_category_id(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value


class Documento(DocumentoInput):
    id: str
