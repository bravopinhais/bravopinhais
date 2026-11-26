from datetime import date

import pytest

from app.core.migration_dates import parse_legacy_date


def test_iso_date_is_unambiguous_and_preserves_original_text():
    result = parse_legacy_date("2021-11-25")

    assert result.original_text == "2021-11-25"
    assert result.normalized_date == date(2021, 11, 25)
    assert result.status == "normalized"
    assert result.rule_id == "iso-ymd-v1"


def test_brazilian_date_requires_explicit_format_hint():
    result = parse_legacy_date("25/11/2021")

    assert result.original_text == "25/11/2021"
    assert result.normalized_date is None
    assert result.status == "ambiguous"


def test_brazilian_date_normalizes_only_with_explicit_hint():
    original = " 25/11/2021 "
    result = parse_legacy_date(original, format_hint="br")

    assert result.original_text == original
    assert result.normalized_date == date(2021, 11, 25)
    assert result.status == "normalized"
    assert result.rule_id == "br-dmy-v1"


def test_ambiguous_day_and_month_is_not_guessed():
    result = parse_legacy_date("01/02/2024")

    assert result.status == "ambiguous"
    assert result.normalized_date is None


def test_impossible_brazilian_date_is_preserved_and_invalid():
    original = "31/02/2024"
    result = parse_legacy_date(original, format_hint="br")

    assert result.original_text == original
    assert result.normalized_date is None
    assert result.status == "invalid"
    assert result.rule_id == "br-dmy-v1"


def test_impossible_iso_date_is_invalid():
    result = parse_legacy_date("2024-02-31")

    assert result.status == "invalid"
    assert result.normalized_date is None


def test_empty_and_whitespace_values_are_not_attempted():
    for original in ("", "   ", None):
        result = parse_legacy_date(original)
        assert result.original_text == original
        assert result.status == "not_attempted"
        assert result.normalized_date is None


def test_unknown_format_is_invalid_and_preserved():
    original = "25-11-2021"
    result = parse_legacy_date(original)

    assert result.original_text == original
    assert result.status == "invalid"
    assert result.normalized_date is None


def test_iso_with_conflicting_hint_is_not_accepted():
    result = parse_legacy_date("2021-11-25", format_hint="br")

    assert result.status == "invalid"
    assert result.normalized_date is None


def test_non_text_input_is_rejected_instead_of_coerced():
    with pytest.raises(TypeError):
        parse_legacy_date(20211125)  # type: ignore[arg-type]
