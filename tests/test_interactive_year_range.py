"""Regression tests for BUG-007: interactive wizard crashes when all records lack year."""

from __future__ import annotations

import pytest

from citationer.cli.interactive_cmd import _year_range
from citationer.models.record import Author, Record


def _r(title: str = "T", year: int | None = 2024) -> Record:
    return Record(
        title=title,
        year=year,
        authors=[Author(full_name="A", order=1)],
        keywords=["x"],
        source_database="T",
    )


class TestBug007Regression:
    """BUG-007: year_range must not raise when all records have year=None."""

    def test_all_year_none_returns_none(self):
        """All records have year=None → (None, None), no ValueError."""
        records = [_r(year=None), _r(year=None), _r(year=None)]
        result = _year_range(records)
        assert result == (None, None)

    def test_mixed_year_values(self):
        """Mixed years → normal min/max."""
        records = [_r(year=2020), _r(year=2024), _r(year=2022), _r(year=None)]
        assert _year_range(records) == (2020, 2024)

    def test_single_record_with_year(self):
        records = [_r(year=2024)]
        assert _year_range(records) == (2024, 2024)

    def test_single_record_no_year(self):
        records = [_r(year=None)]
        assert _year_range(records) == (None, None)

    def test_empty_records(self):
        assert _year_range([]) == (None, None)

    def test_year_zero_included(self):
        """year=0 is a valid year (rare but possible)."""
        records = [_r(year=0), _r(year=2024)]
        assert _year_range(records) == (0, 2024)

    def test_no_false_min_year_zero(self):
        """year=None records must NOT be treated as year=0.

        Pre-fix: \`r.year for r in records if r.year\` would skip None.
        This still worked but the OLD code called \`min(...if r.year)\`
        which DID skip None — but min() over empty iterator raises
        ValueError.  Verify our helper does not.
        """
        records = [_r(year=None)]
        # Should not raise
        result = _year_range(records)
        assert result == (None, None)
        # And specifically not (0, 0) which would imply year=0 was used
        assert 0 not in result