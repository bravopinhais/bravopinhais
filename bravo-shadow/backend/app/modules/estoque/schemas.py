from pydantic import BaseModel, ConfigDict, Field

class EstoqueInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    item: str = Field(min_length=1)
    quantidade: int = 1
    minimo: int = 0
    maximo: int = 0
    etiqueta: str = ''
    fotoNome: str = ''
    fotoCompactadaGzip: str = ''
    # Campos adicionais solicitados para rastreabilidade de origem do produto.
    marca: str = ''
    linha: str = ''
    fabricante: str = ''
    dataCadastro: str = ''

class EstoqueItem(EstoqueInput):
    id: str
