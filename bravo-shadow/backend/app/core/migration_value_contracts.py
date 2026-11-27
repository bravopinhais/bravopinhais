"""Pure strict value validators for Bravo Shadow migration review."""
from __future__ import annotations
import base64, binascii, hashlib, zlib
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

class MigrationValueError(ValueError):
    pass

@dataclass(frozen=True, slots=True)
class DecimalContract:
    precision: int
    scale: int
    allow_negative: bool = True

@dataclass(frozen=True, slots=True)
class CompressedDocumentAssessment:
    encoded_bytes: int
    compressed_bytes: int
    uncompressed_bytes: int
    sha256_uncompressed: str
    codec: str

def parse_decimal_text(value: Any, contract: DecimalContract) -> Decimal:
    if not isinstance(value, str) or not value.strip():
        raise MigrationValueError("valor decimal deve ser texto não vazio.")
    try:
        result = Decimal(value.strip())
    except InvalidOperation as exc:
        raise MigrationValueError("valor decimal inválido.") from exc
    if not result.is_finite():
        raise MigrationValueError("NaN e infinito não são permitidos.")
    fractional = max(0, -result.as_tuple().exponent)
    integer = max(0, result.copy_abs().adjusted() + 1) if result else 0
    if fractional > contract.scale or integer > contract.precision - contract.scale:
        raise MigrationValueError("precisão ou escala decimal excedida.")
    if not contract.allow_negative and result < 0:
        raise MigrationValueError("valor negativo não permitido.")
    return result

def parse_iso_date(value: Any) -> date:
    if not isinstance(value, str) or not value:
        raise MigrationValueError("data deve ser texto ISO YYYY-MM-DD.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise MigrationValueError("data ISO inválida.") from exc
    if parsed.isoformat() != value:
        raise MigrationValueError("data deve usar exatamente YYYY-MM-DD.")
    return parsed

def parse_iso_datetime_with_timezone(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise MigrationValueError("data/hora deve ser texto ISO 8601.")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MigrationValueError("data/hora ISO 8601 inválida.") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MigrationValueError("data/hora precisa informar fuso.")
    return parsed

def validate_literal(value: Any, allowed: frozenset[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise MigrationValueError("valor fora do conjunto literal permitido.")
    return value

def assess_base64_deflate_document(value: Any, *, max_encoded_bytes: int = 20_000_000,
                                   max_uncompressed_bytes: int = 100_000_000) -> CompressedDocumentAssessment:
    if not isinstance(value, str) or not value:
        raise MigrationValueError("documento compactado deve ser Base64 textual.")
    try:
        encoded = value.encode("ascii")
        if len(encoded) > max_encoded_bytes:
            raise MigrationValueError("documento excede limite codificado.")
        packed = base64.b64decode(encoded, validate=True)
    except (UnicodeEncodeError, binascii.Error) as exc:
        raise MigrationValueError("Base64 inválido.") from exc
    if not packed:
        raise MigrationValueError("conteúdo compactado vazio.")
    for codec, window in (("zlib_deflate", zlib.MAX_WBITS), ("gzip", zlib.MAX_WBITS | 16)):
        dec = zlib.decompressobj(window)
        try:
            raw = dec.decompress(packed, max_uncompressed_bytes + 1)
            if len(raw) > max_uncompressed_bytes or dec.unconsumed_tail:
                raise MigrationValueError("conteúdo descompactado excede limite.")
            raw += dec.flush()
            if len(raw) > max_uncompressed_bytes:
                raise MigrationValueError("conteúdo descompactado excede limite.")
            if not dec.eof or dec.unused_data:
                raise MigrationValueError("fluxo comprimido incompleto ou com dados extras.")
            return CompressedDocumentAssessment(len(encoded), len(packed), len(raw),
                                                 hashlib.sha256(raw).hexdigest(), codec)
        except zlib.error:
            continue
    raise MigrationValueError("compressão não reconhecida ou corrompida.")
