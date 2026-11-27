import base64, gzip, zlib
from decimal import Decimal
import pytest
from app.core.migration_value_contracts import (
    DecimalContract, MigrationValueError, assess_base64_deflate_document,
    parse_decimal_text, parse_iso_date, parse_iso_datetime_with_timezone, validate_literal,
)

def test_decimal_is_exact_text_and_respects_scale_precision():
    assert parse_decimal_text("123.450", DecimalContract(14, 3)) == Decimal("123.450")
    for value in (123.45, "1.234", "NaN", "Infinity", "1000000000000.00"):
        with pytest.raises(MigrationValueError):
            parse_decimal_text(value, DecimalContract(14, 2))

def test_decimal_can_forbid_negative_values():
    with pytest.raises(MigrationValueError):
        parse_decimal_text("-0.01", DecimalContract(14, 2, False))

def test_dates_are_canonical_and_datetime_requires_timezone():
    assert parse_iso_date("2026-11-27").isoformat() == "2026-11-27"
    with pytest.raises(MigrationValueError): parse_iso_date("27/11/2026")
    with pytest.raises(MigrationValueError): parse_iso_datetime_with_timezone("2026-11-27T10:00:00")

def test_literal_enum_is_exact():
    assert validate_literal("Entrada", frozenset({"Entrada", "Saída"})) == "Entrada"
    with pytest.raises(MigrationValueError): validate_literal("entrada", frozenset({"Entrada", "Saída"}))

@pytest.mark.parametrize("packed,codec", [
    (zlib.compress(b"synthetic file"), "zlib_deflate"),
    (gzip.compress(b"synthetic file"), "gzip"),
])
def test_document_validation_reports_only_metadata(packed, codec):
    report = assess_base64_deflate_document(base64.b64encode(packed).decode())
    assert report.codec == codec and report.uncompressed_bytes == 14
    assert len(report.sha256_uncompressed) == 64
    assert not hasattr(report, "content")

def test_document_rejects_invalid_base64_corruption_and_bombs():
    for value in ("bad base64!", base64.b64encode(b"broken").decode()):
        with pytest.raises(MigrationValueError): assess_base64_deflate_document(value)
    packed = base64.b64encode(zlib.compress(b"x" * 1000)).decode()
    with pytest.raises(MigrationValueError):
        assess_base64_deflate_document(packed, max_uncompressed_bytes=100)
