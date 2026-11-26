"""Pure parsing helpers for historical Bravo migration dates.

The parser never rewrites the source value. A normalized date is derived only
when the input format is explicitly known or unambiguous.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
from typing import Literal

DateStatus = Literal["not_attempted", "normalized", "ambiguous", "invalid"]
DateFormat = Literal["iso", "br"]


@dataclass(frozen=True, slots=True)
class LegacyDateResult:
    original_text: str | None
    normalized_date: date | None
    status: DateStatus
    rule_id: str | None


_ISO_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BR_PATTERN = re.compile(r"^\d{2}/\d{2}/\d{4}$")


def parse_legacy_date(
    value: str | None,
    *,
    format_hint: DateFormat | None = None,
) -> LegacyDateResult:
    """Parse only documented date formats while preserving the exact input.

    ISO YYYY-MM-DD is self-identifying. DD/MM/YYYY requires format_hint="br"
    because slash-separated dates are otherwise ambiguous. No time or timezone
    is inferred. Invalid and unrecognized strings remain available verbatim.
    """
    if value is not None and not isinstance(value, str):
        raise TypeError("A data histórica deve ser texto ou None.")

    if value is None or not value.strip():
        return LegacyDateResult(value, None, "not_attempted", None)

    candidate = value.strip()

    if _ISO_PATTERN.fullmatch(candidate):
        if format_hint not in (None, "iso"):
            return LegacyDateResult(value, None, "invalid", None)
        try:
            parsed = date.fromisoformat(candidate)
        except ValueError:
            return LegacyDateResult(value, None, "invalid", None)
        return LegacyDateResult(value, parsed, "normalized", "iso-ymd-v1")

    if _BR_PATTERN.fullmatch(candidate):
        if format_hint is None:
            return LegacyDateResult(value, None, "ambiguous", None)
        if format_hint != "br":
            return LegacyDateResult(value, None, "invalid", None)
        day, month, year = (int(part) for part in candidate.split("/"))
        try:
            parsed = date(year, month, day)
        except ValueError:
            return LegacyDateResult(value, None, "invalid", "br-dmy-v1")
        return LegacyDateResult(value, parsed, "normalized", "br-dmy-v1")

    return LegacyDateResult(value, None, "invalid", None)
