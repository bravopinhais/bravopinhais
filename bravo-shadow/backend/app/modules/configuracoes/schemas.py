from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModuloEstado(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chave: str
    nome: str
    grupo: str
    ativo: bool


class ModuloEstadoUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ativo: bool


class ModulosAcaoEmMassa(BaseModel):
    model_config = ConfigDict(extra="forbid")
    acao: Literal["ativar_todos", "desativar_operacionais"]
