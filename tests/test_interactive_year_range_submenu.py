"""Regression test for code-review finding #1:

Interactive wizard's stats sub-menu (1 → 1) printed literal "None–None"
when all records had year=None.  Stats overview table should show "-" or
similar placeholder, not raw None.
"""

from __future__ import annotations

from pathlib import Path

from citationer.models.record import Author, Record
from citationer.utils.database import CitationDatabase
from citationer.utils.serialization import record_to_db_serializable
from tests._factories import make_record as _r


def _setup_db_with_no_year_records(clean_cwd: Path) -> None:
    """Insert 3 records, all with year=None."""
    db_dir = clean_cwd / ".citationer"
    db_dir.mkdir(exist_ok=True)
    db = CitationDatabase(db_dir / "cache.db")
    db.initialize()
    for r in [_r(f"P{i}") for i in range(3)]:
        payload = record_to_db_serializable(r)
        db.insert_record(
            record_data=payload["record_data"],
            authors=payload["authors"],
            keywords=payload["keywords"],
            institutions=payload["institutions"],
        )
    db.close()


class TestInteractiveStatsSubmenu:
    """Submenu shouldn't print literal 'None–None' for year range."""

    def test_overview_returns_none_min_max(self):
        """Sanity: stats.overview() returns (None, None) when no years."""
        from citationer.analysis.stats import StatsEngine

        records = [
            Record(title="A", year=None, authors=[Author(full_name="A", order=1)]),
            Record(title="B", year=None, authors=[Author(full_name="B", order=1)]),
        ]
        engine = StatsEngine(records)
        s = engine.overview()
        assert s.year_min is None
        assert s.year_max is None

    def test_submenu_year_range_uses_placeholder(self, clean_cwd):
        """Verify _interactive_stats has a None-guard before formatting."""
        _setup_db_with_no_year_records(clean_cwd)
        import inspect

        from citationer.cli import interactive_cmd as ic

        source = inspect.getsource(ic._interactive_stats)
        assert "y_min, y_max = s.year_min, s.year_max" in source, (
            "_interactive_stats must still read year_min/year_max"
        )
        # The production code must guard against None before formatting.
        guarded = (
            "if y_min is not None" in source
            or "if s.year_min is not None" in source
            or "if year_min is not None" in source
        )
        assert guarded, (
            "_interactive_stats must guard against None year_min before "
            "formatting.  StatsEngine.overview() returns (None, None) when "
            "no records have a year, so f-string formatting produces the "
            "literal 'None-None'."
        )
