"""Synthetic tests for explicit legacy date normalization."""
import pytest
from app.core.migration_date_parser import normalize_legacy_date

def test_iso_date_requires_explicit_rule_and_preserves_raw():
    raw = "2021-11-25"
    assert normalize_legacy_date(raw).status == "not_attempted"
    result = normalize_legacy_date(raw, rule_id="iso_ymd_v1")
    assert (result.raw_value, result.normalized_value, result.status) == (raw, raw, "normalized")

def test_brazilian_date_is_interpreted_only_with_dmy_rule():
    raw = "25/11/2021"
    assert normalize_legacy_date(raw, rule_id="pt_br_dmy_v1").normalized_value == "2021-11-25"
    assert normalize_legacy_date(raw, rule_id="iso_ymd_v1").status == "invalid"

@pytest.mark.parametrize("raw", ["31/02/2024", "29/02/2023", "1/2/2024", " 25/11/2021", "25/11/2021 "])
def test_invalid_or_noncanonical_brazilian_dates_are_not_repaired(raw):
    result = normalize_legacy_date(raw, rule_id="pt_br_dmy_v1")
    assert result.status == "invalid"
    assert result.raw_value == raw
    assert result.normalized_value is None

def test_empty_and_missing_rule_remain_unmodified():
    assert normalize_legacy_date("").status == "not_attempted"
    result = normalize_legacy_date("", rule_id="pt_br_dmy_v1")
    assert result.raw_value == "" and result.normalized_value is None

def test_unknown_rule_and_non_text_are_rejected():
    with pytest.raises(ValueError):
        normalize_legacy_date("2021-11-25", rule_id="guess")
    with pytest.raises(TypeError):
        normalize_legacy_date(None)
