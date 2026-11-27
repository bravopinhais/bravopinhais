import base64
import binascii
import zlib

from pathlib import PurePath

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

MAX_DOCUMENT_BYTES = 5 * 1024 * 1024
MAX_COMPRESSED_BASE64_CHARS = 8 * 1024 * 1024


class DocumentoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pasta: str = Field(default="Geral", min_length=1, max_length=120)
    categoriaId: str | None = Field(default=None, max_length=100)
    titulo: str = Field(min_length=1, max_length=200)
    nomeArquivo: str = Field(min_length=1, max_length=255)
    arquivoCompactadoGzip: str = Field(
        min_length=1,
        max_length=MAX_COMPRESSED_BASE64_CHARS,
    )

    @field_validator("pasta", "titulo", "nomeArquivo", mode="before")
    @classmethod
    def trim_text_metadata(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("nomeArquivo")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        if value in {".", ".."} or any(char in value for char in ("/", "\\", "\x00")) or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("O nome do arquivo não pode conter caminhos.")
        return value

    @field_validator("categoriaId", mode="before")
    @classmethod
    def normalize_category_id(cls, value):
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("arquivoCompactadoGzip")
    @classmethod
    def validate_gzip_base64(cls, value: str, info: ValidationInfo) -> str:
        try:
            compressed = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("O arquivo precisa estar codificado em Base64 válido.") from exc

        if not compressed or len(compressed) > MAX_DOCUMENT_BYTES + 65536:
            raise ValueError("O arquivo compactado excede o limite permitido.")

        try:
            decoder = zlib.decompressobj(wbits=16 + zlib.MAX_WBITS)
            content = decoder.decompress(compressed, MAX_DOCUMENT_BYTES + 1)
            if len(content) > MAX_DOCUMENT_BYTES or decoder.unconsumed_tail:
                raise ValueError("O arquivo original excede o limite de 5 MiB.")
            remaining = MAX_DOCUMENT_BYTES + 1 - len(content)
            if remaining > 0:
                content += decoder.flush(remaining)
            if len(content) > MAX_DOCUMENT_BYTES:
                raise ValueError("O arquivo original excede o limite de 5 MiB.")
            if not decoder.eof or decoder.unused_data:
                raise ValueError("O conteúdo não é um arquivo Gzip íntegro.")
            if not content:
                raise ValueError("O arquivo original não pode estar vazio.")
            filename = info.data.get("nomeArquivo", "")
            extension = PurePath(filename).suffix.lower().lstrip(".")
            allowed = {
                "pdf", "png", "jpg", "jpeg", "gif", "webp",
                "txt", "csv", "doc", "docx", "xls", "xlsx", "odt", "ods",
            }
            if extension not in allowed:
                raise ValueError("Formato de arquivo não permitido.")
            signatures = {
                "pdf": content.startswith(b"%PDF-"),
                "png": content.startswith(b"\x89PNG\r\n\x1a\n"),
                "jpg": content.startswith(b"\xff\xd8\xff"),
                "jpeg": content.startswith(b"\xff\xd8\xff"),
                "gif": content.startswith((b"GIF87a", b"GIF89a")),
                "webp": len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP",
                "doc": content.startswith(bytes.fromhex("D0CF11E0A1B11AE1")),
                "xls": content.startswith(bytes.fromhex("D0CF11E0A1B11AE1")),
                "docx": content.startswith(b"PK\x03\x04"),
                "xlsx": content.startswith(b"PK\x03\x04"),
                "odt": content.startswith(b"PK\x03\x04"),
                "ods": content.startswith(b"PK\x03\x04"),
            }
            if extension in {"txt", "csv"}:
                try:
                    content.decode("utf-8-sig")
                except UnicodeDecodeError as exc:
                    raise ValueError("Arquivos TXT/CSV precisam estar codificados em UTF-8.") from exc
                if b"\x00" in content:
                    raise ValueError("Arquivos TXT/CSV não podem conter bytes nulos.")
            elif not signatures.get(extension, False):
                raise ValueError("O conteúdo não corresponde ao formato indicado no nome do arquivo.")
        except zlib.error as exc:
            raise ValueError("O conteúdo Gzip é inválido ou está corrompido.") from exc
        return value


class Documento(BaseModel):
    id: str
    pasta: str
    categoriaId: str | None = None
    titulo: str
    nomeArquivo: str
    arquivoCompactadoGzip: str


class DocumentoResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    pasta: str
    categoriaId: str | None = None
    titulo: str
    nomeArquivo: str
