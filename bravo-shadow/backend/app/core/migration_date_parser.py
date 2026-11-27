"""Explicit, lossless date interpretation for legacy migration values.

The parser always preserves the original string and never infers a locale,
year, time, or timezone. It performs no I/O or persistence.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

DateRule = Literal["iso_ymd_v1", "pt_br_dmy_v1"]
_ALLOWED_RULES = frozenset({"iso_ymd_v1", "pt_br_dmy_v1"})

@dataclass(frozen=True, slots=True)
class DateNormalization:
    raw_value: str
    normalized_value: str | None
    status: str
    rule_id: str | None

def normalize_legacy_date(raw_value: str, *, rule_id: DateRule | None = None) -> DateNormalization:
    """Normalize only an explicitly selected, versioned date format.

    Status values: not_attempted, normalized, invalid. The raw input is
    returned byte-for-character unchanged, including whitespace and separators.
    """
    if not isinstance(raw_value, str):
        raise TypeError("raw_value deve ser texto.")
    if rule_id is None:
        return DateNormalization(raw_value, None, "not_attempted", None)
    if not isinstance(rule_id, str) or rule_id not in _ALLOWED_RULES:
        raise ValueError("regra de data não reconhecida.")
    if not raw_value:
        return DateNormalization(raw_value, None, "not_attempted", rule_id)
    fmt = "%Y-%m-%d" if rule_id == "iso_ymd_v1" else "%d/%m/%Y"
    try:
        parsed = datetime.strptime(raw_value, fmt).date()
    except (ValueError, TypeError):
        return DateNormalization(raw_value, None, "invalid", rule_id)
    if parsed.strftime(fmt) != raw_value:
        return DateNormalization(raw_value, None, "invalid", rule_id)
    return DateNormalization(raw_value, parsed.isoformat(), "normalized", rule_id)
