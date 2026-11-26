from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

class UsuarioInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    nome: str = Field(min_length=1, max_length=160)
    loja: str = Field(default="Guardiões do Bravo", min_length=1, max_length=120)
    cargo: str = Field(min_length=1, max_length=100)
    perfil: Literal["Admin", "Operador"] = "Operador"
    status: Literal["Ativo", "Inativo"] = "Ativo"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("nome", "loja", "cargo")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()

class Usuario(UsuarioInput):
    id: str

class UsuarioCadastroInput(BaseModel):
    """Dados para proposta de cadastro; não define perfil nem status."""
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    nome: str = Field(min_length=1, max_length=160)
    loja: str = Field(default="Guardiões do Bravo", min_length=1, max_length=120)
    cargo: str = Field(min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("nome", "loja", "cargo")
    @classmethod
    def trim_text(cls, value: str) -> str:
        return value.strip()


class UsuarioDadosCadastraisUpdateInput(BaseModel):
    """Atualização cadastral sem troca de identidade/e-mail."""
    model_config = ConfigDict(extra="forbid")
    nome: str | None = Field(default=None, min_length=1, max_length=160)
    loja: str | None = Field(default=None, min_length=1, max_length=120)
    cargo: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("nome", "loja", "cargo")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None


class UsuarioAdministracaoInput(BaseModel):
    """Mudanças privilegiadas; requer autorização administrativa separada."""
    model_config = ConfigDict(extra="forbid")
    perfil: Literal["Admin", "Operador"]
    status: Literal["Ativo", "Inativo"]
\n