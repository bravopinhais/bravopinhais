"""Field-level, non-transforming value assessment for high-risk legacy records."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import math
from typing import Any, Mapping

from app.core.migration_value_contracts import (
    MigrationValueError, assess_base64_deflate_document,
    parse_iso_datetime_with_timezone, validate_literal,
)

@dataclass(frozen=True, slots=True)
class ValueIssue:
    field: str
    code: str
    message: str

@dataclass(frozen=True, slots=True)
class RecordValueAssessment:
    contract_key: str
    status: str
    issues: tuple[ValueIssue, ...]

_ENUMS = {
    ("financeiro", "tipo"): frozenset({"Receber", "Pagar"}),
    ("acertos_estoque", "tipo"): frozenset({"Entrada", "Saída"}),
}
_DECIMAL_FIELDS = {
    "financeiro": {"valor": (14, 2, True)},
    "estoque": {"quantidade": (14, 3, False), "minimo": (14, 3, False), "maximo": (14, 3, False)},
    "acertos_estoque": {"quantidade": (14, 3, False)},
}
_DOCUMENT_FIELDS = {
    "documentos": ("arquivoCompactadoGzip",),
    "estoque": ("fotoCompactadaGzip",),
}

def assess_special_record_values(contract_key: str, record: Mapping[str, Any]) -> RecordValueAssessment:
    """Return safe issue codes only; never mutate or echo source values."""
    issues: list[ValueIssue] = []
    if contract_key not in {"financeiro", "documentos", "estoque", "acertos_estoque"}:
        return RecordValueAssessment(contract_key, "unsupported_contract", (
            ValueIssue("", "unsupported_contract", "Contrato especializado não reconhecido."),
        ))
    for (key, field), allowed in _ENUMS.items():
        if key == contract_key and field in record:
            try:
                validate_literal(record[field], allowed)
            except MigrationValueError:
                issues.append(ValueIssue(field, "invalid_literal", "Valor não pertence ao conjunto literal aprovado."))
    for field, (precision, scale, allow_negative) in _DECIMAL_FIELDS.get(contract_key, {}).items():
        if field not in record or record[field] is None:
            continue
        value = record[field]
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            issues.append(ValueIssue(field, "invalid_numeric_type", "Tipo numérico não suportado pelo contrato."))
            continue
        try:
            numeric = Decimal(value) if isinstance(value, str) else Decimal(str(value))
        except InvalidOperation:
            issues.append(ValueIssue(field, "invalid_numeric_value", "Valor numérico inválido."))
            continue
        if not numeric.is_finite():
            issues.append(ValueIssue(field, "non_finite_number", "NaN e infinito não são permitidos."))
            continue
        fractional = max(0, -numeric.as_tuple().exponent)
        integer = max(0, numeric.copy_abs().adjusted() + 1) if numeric else 0
        if fractional > scale or integer > precision - scale:
            issues.append(ValueIssue(field, "numeric_precision_exceeded", "Precisão/escala excede o tipo SQL de destino."))
        if not allow_negative and numeric < 0:
            issues.append(ValueIssue(field, "negative_not_allowed", "O destino não aceita valor negativo."))
        if contract_key == "financeiro" and not isinstance(value, str):
            issues.append(ValueIssue(field, "decimal_precision_unproven", "Número JSON legado não comprova precisão decimal exata; exige aprovação e relatório de perda."))
        elif contract_key in {"estoque", "acertos_estoque"} and not isinstance(value, str):
            issues.append(ValueIssue(field, "numeric_conversion_review", "Número legado exige regra explícita de conversão para Decimal; nenhum arredondamento foi aplicado."))
    if contract_key == "acertos_estoque" and "data" in record:
        try:
            parse_iso_datetime_with_timezone(record["data"])
        except MigrationValueError:
            issues.append(ValueIssue("data", "datetime_timezone_review", "Data legada não está em ISO 8601 com fuso; preservar original e revisar antes do TIMESTAMPTZ."))
    for field in _DOCUMENT_FIELDS.get(contract_key, ()):
        if field in record and record[field] not in (None, ""):
            try:
                assess_base64_deflate_document(record[field])
            except MigrationValueError:
                issues.append(ValueIssue(field, "compressed_document_invalid", "Base64/fluxo comprimido inválido ou acima dos limites."))
    return RecordValueAssessment(contract_key, "review_required" if issues else "shape_valid_review_mapping", tuple(issues))
