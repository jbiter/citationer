"""Shared year-range helpers."""

from __future__ import annotations

from collections.abc import Iterable

from citationer.models.record import Record


def year_range(records: Iterable[Record]) -> tuple[int | None, int | None]:
    """Return (min_year, max_year) across records with a valid year.

    Returns (None, None) when no record has a year.  year=0 counts as
    a valid year (not treated as missing).
    """
    years = [r.year for r in records if r.year is not None]
    if not years:
        return None, None
    return min(years), max(years)
