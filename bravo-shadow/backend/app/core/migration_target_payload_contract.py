"""Strict Python-to-PostgreSQL payload checks for migration writes.

Validation is intentionally non-coercive: no rounding, stringification,
timezone guessing, enum normalization, or implicit float-to-decimal conversion.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import math
import re
from typing import Any, Mapping

class TargetPayloadContractError(ValueError):
    """A migration payload does not satisfy its reviewed SQL value contract."""

NUMERIC_COLUMNS: dict[tuple[str, str], tuple[int, int, str]] = {
    ("formas_monetarias", "multa_pct"): (None, None, "finite_float"),
    ("financeiro", "valor"): (14, 2, "any"),
    ("contas_bancarias", "saldo"): (14, 2, "any"),
    ("estoque", "quantidade"): (14, 3, "nonnegative"),
    ("estoque", "minimo"): (14, 3, "nonnegative"),
    ("estoque", "maximo"): (14, 3, "nonnegative"),
    ("estoque", "valor_unitario"): (14, 2, "nonnegative"),
    ("acertos_estoque", "quantidade"): (14, 3, "positive"),
}
DATE_COLUMNS = {("estoque", "data_cadastro")}
TIMESTAMPTZ_COLUMNS = {("acertos_estoque", "data")}
NULLABLE_COLUMNS = {\n    ("financeiro", "plano_conta_id"),\n    ("estoque", "data_cadastro"),\n    ("documentos", "categoria_id"),\n    ("acertos_estoque", "motivo_id"),\n}\nENUMS = {
    ("plano_contas", "tipo"): {"Receita", "Despesa"},
    ("financeiro", "tipo"): {"Receber", "Pagar"},
    ("estoque", "status"): {"Ativo", "Inativo"},
    ("acertos_estoque", "tipo"): {"Entrada", "Saída"},
}
_DECIMAL_TEXT = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")

def _decimal(value: Any, *, collection: str, column: str,
             precision: int, scale: int, rule: str) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise TargetPayloadContractError(f"{collection}.{column}: decimal_exige_texto_int_ou_decimal")
    if isinstance(value, Decimal):
        number = value
    elif isinstance(value, int):
        number = Decimal(value)
    elif isinstance(value, str) and _DECIMAL_TEXT.fullmatch(value):
        try:
            number = Decimal(value)
        except InvalidOperation as exc:
            raise TargetPayloadContractError(f"{collection}.{column}: decimal_invalido") from exc
    else:
        raise TargetPayloadContractError(f"{collection}.{column}: decimal_invalido")
    if not number.is_finite():
        raise TargetPayloadContractError(f"{collection}.{column}: decimal_nao_finito")
    sign, digits, exponent = number.as_tuple()
    fractional = max(-exponent, 0)
    integer_digits = max(len(digits) - fractional, 0)
    if fractional > scale or integer_digits > precision - scale:
        raise TargetPayloadContractError(f"{collection}.{column}: numeric_precision_or_scale_exceeded")
    if rule == "nonnegative" and number < 0:
        raise TargetPayloadContractError(f"{collection}.{column}: negative_value_not_allowed")
    if rule == "positive" and number <= 0:
        raise TargetPayloadContractError(f"{collection}.{column}: positive_value_required")
    return number

def _aware_datetime(value: Any, collection: str, column: str) -> None:
    parsed = value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise TargetPayloadContractError(f"{collection}.{column}: timestamp_invalid") from exc
    if not isinstance(parsed, datetime) or parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TargetPayloadContractError(f"{collection}.{column}: timezone_required")

def validate_target_payload(collection: str, payload: Mapping[str, Any]) -> None:
    """Validate known target SQL value types without modifying payload."""
    if not isinstance(collection, str) or not isinstance(payload, Mapping):
        raise TypeError("coleção e payload inválidos.")
    for column, value in payload.items():
        key = (collection, column)
        if value is None:
            # SQL NULLability is enforced by the DDL; preserve explicit NULL.
            continue
        if key in NUMERIC_COLUMNS:
            precision, scale, rule = NUMERIC_COLUMNS[key]
            if rule == "finite_float":
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise TargetPayloadContractError(f"{collection}.{column}: finite_float_required")
            else:
                _decimal(value, collection=collection, column=column,
                         precision=precision, scale=scale, rule=rule)
            continue
        if key in DATE_COLUMNS:
            if isinstance(value, datetime) or not (
                isinstance(value, date) or
                (isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))
            ):
                raise TargetPayloadContractError(f"{collection}.{column}: iso_date_required")
            if isinstance(value, str):
                try:
                    date.fromisoformat(value)
                except ValueError as exc:
                    raise TargetPayloadContractError(f"{collection}.{column}: iso_date_invalid") from exc
            continue
        if key in TIMESTAMPTZ_COLUMNS:
            _aware_datetime(value, collection, column)
            continue
        if key in ENUMS:
            if not isinstance(value, str) or value not in ENUMS[key]:
                raise TargetPayloadContractError(f"{collection}.{column}: enum_literal_invalid")
            continue
        if not isinstance(value, str):
            raise TargetPayloadContractError(f"{collection}.{column}: text_value_required")
