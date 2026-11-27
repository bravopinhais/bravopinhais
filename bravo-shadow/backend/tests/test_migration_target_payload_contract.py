from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.core.migration_target_payload_contract import (
    TargetPayloadContractError,
    validate_target_payload,
)

@pytest.mark.parametrize("value", [12.34, True, "1,25", "NaN", "Infinity"])
def test_financial_decimal_rejects_ambiguous_or_lossy_values(value):
    with pytest.raises(TargetPayloadContractError):
        validate_target_payload("financeiro", {"valor": value})

def test_financial_decimal_accepts_exact_values_without_mutating_payload():
    payload = {"valor": Decimal("123.45"), "tipo": "Receber", "historico": "synthetic"}
    before = dict(payload)
    validate_target_payload("financeiro", payload)
    assert payload == before

@pytest.mark.parametrize("value", ["1.2345", "1000000000000.00", -0.001])
def test_stock_numeric_rejects_scale_overflow_and_negative(value):
    with pytest.raises(TargetPayloadContractError):
        validate_target_payload("estoque", {"quantidade": value})

def test_stock_numeric_accepts_three_decimal_places():
    validate_target_payload("estoque", {"quantidade": "12.345", "minimo": 0})

@pytest.mark.parametrize("value", [
    Decimal("1E+13"),
    Decimal("-1E+12"),
])
def test_numeric_precision_counts_positive_decimal_exponents(value):
    with pytest.raises(TargetPayloadContractError, match="numeric_precision_or_scale_exceeded"):
        validate_target_payload("financeiro", {"valor": value})

def test_numeric_precision_accepts_maximum_integer_digits_and_exponent_zero():
    validate_target_payload("financeiro", {"valor": Decimal("1E+12")})
    validate_target_payload("financeiro", {"valor": Decimal("0E+100")})

def test_finite_float_rejects_integer_outside_float_range():
    with pytest.raises(TargetPayloadContractError, match="finite_float_required"):
        validate_target_payload("formas_monetarias", {"multa_pct": 10 ** 1000})

@pytest.mark.parametrize("value", ["2026-02-30", "27/11/2026", "2026-11-27T00:00:00"])
def test_stock_date_requires_real_iso_calendar_date(value):
    with pytest.raises(TargetPayloadContractError):
        validate_target_payload("estoque", {"data_cadastro": value})

def test_stock_date_accepts_iso_date_or_date_object():
    validate_target_payload("estoque", {"data_cadastro": "2026-11-27"})
    validate_target_payload("estoque", {"data_cadastro": date(2026, 11, 27)})

@pytest.mark.parametrize("value", ["2026-11-27T12:00:00", "27/11/2026", datetime(2026, 11, 27)])
def test_movement_timestamp_requires_explicit_timezone(value):
    with pytest.raises(TargetPayloadContractError):
        validate_target_payload("acertos_estoque", {"data": value})

def test_movement_timestamp_accepts_aware_values():
    validate_target_payload("acertos_estoque", {"data": "2026-11-27T12:00:00-03:00"})
    validate_target_payload("acertos_estoque", {"data": datetime(2026, 11, 27, tzinfo=timezone.utc)})

@pytest.mark.parametrize("value", ["entrada", "Entrada ", "SAÍDA"])
def test_enums_are_exact_literals(value):
    with pytest.raises(TargetPayloadContractError):
        validate_target_payload("acertos_estoque", {"tipo": value})

def test_text_fields_do_not_implicitly_stringify():
    with pytest.raises(TargetPayloadContractError):
        validate_target_payload("estoque", {"item": 123})

@pytest.mark.parametrize("collection,column", [
    ("financeiro", "historico"),
    ("estoque", "item"),
    ("documentos", "titulo"),
    ("acertos_estoque", "quantidade"),
])
def test_non_nullable_columns_reject_explicit_null(collection, column):
    with pytest.raises(TargetPayloadContractError, match="null_not_allowed"):
        validate_target_payload(collection, {column: None})

def test_nullable_foreign_keys_and_stock_date_keep_explicit_null():
    validate_target_payload("financeiro", {"plano_conta_id": None})
    validate_target_payload("documentos", {"categoria_id": None})
    validate_target_payload("estoque", {"data_cadastro": None})
    validate_target_payload("acertos_estoque", {"motivo_id": None})
