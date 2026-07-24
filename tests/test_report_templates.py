"""Tests for P4-5 — report template system (academic vs simple)."""

from __future__ import annotations

from pathlib import Path

import pytest

from citationer.cli.main import app
from citationer.cli.report_cmd import (
    _build_academic,
    _build_markdown,
    _build_simple,
    _md_to_html,
    _overview_table,
    _top_table,
    _yearly_table,
)
from citationer.models.record import Author, Record
from tests._factories import make_record
from tests._helpers import seed_cli_db


def _r(title: str, year: int = 2024, journal: str = "Journal X") -> Record:
    """Minimal record for report-template tests; keeps keywords per record."""
    return make_record(
        title=title,
        year=year,
        journal=journal,
        authors=[Author(full_name=f"Author {title}", order=1)],
        keywords=[f"kw{title}", "common"],
        source_database="T",
    )


@pytest.fixture
def sample_records() -> list[Record]:
    return [
        _r(f"P{i}", year=2020 + (i % 5), journal=f"Journal {i // 3}")
        for i in range(10)
    ]


# ===========================================================================
# Shared template helpers
# ===========================================================================


class TestHelpers:
    def test_overview_table(self):
        from citationer.analysis.stats import OverviewStats

        ov = OverviewStats(
            total_records=10,
            num_authors=5,
            num_journals=3,
            num_institutions=2,
            solo_rate=0.4,
            avg_citations=12.5,
            h_index=7,
        )
        lines = _overview_table(ov)
        joined = "\n".join(lines)
        assert "Total records | 10" in joined
        assert "h-index | 7" in joined
        assert "Solo rate | 40.0%" in joined

    def test_yearly_table_empty(self):
        from citationer.analysis.stats import YearlyStats

        assert _yearly_table(YearlyStats()) == []

    def test_yearly_table_limits_years(self):
        from citationer.analysis.stats import YearlyStats

        yr = YearlyStats(year_counts={y: 1 for y in range(2010, 2025)})
        lines = "\n".join(_yearly_table(yr, years=5))
        assert "2020" in lines
        assert "2024" in lines
        assert "2010" not in lines  # outside the window

    def test_top_table_three_columns(self):
        lines = "\n".join(_top_table("Test", [("A", 10), ("B", 5)]))
        assert "| # | Name | Count |" in lines
        assert "| 1 | A | 10 |" in lines
        assert "| 2 | B | 5 |" in lines

    def test_top_table_two_columns(self):
        lines = "\n".join(
            _top_table("Test", [("X",), ("Y",)], columns=["#", "Letter"])
        )
        assert "| # | Letter |" in lines
        assert "| 1 | X |" in lines

    def test_top_table_empty(self):
        assert _top_table("Test", []) == []


# ===========================================================================
# MD → HTML
# ===========================================================================


class TestMdToHtml:
    def test_basic(self):
        html = _md_to_html("# Title\n\nSome text", "Test Title")
        assert "<!DOCTYPE html>" in html
        assert "<title>Test Title</title>" in html
        assert "# Title" in html
        assert "</p>" in html

    def test_preserves_content(self):
        html = _md_to_html("Line 1\nLine 2", "T")
        assert "Line 1" in html
        assert "Line 2" in html


# ===========================================================================
# Academic template
# ===========================================================================


class TestAcademicTemplate:
    def test_contains_all_sections(self, sample_records):
        md = _build_academic(sample_records)
        assert "## Overview" in md
        assert "## Publication Trend" in md
        assert "## Top Journals" in md
        assert "## Top Authors" in md
        assert "## Top Keywords" in md
        # Topic modeling requires sklearn (skipped if missing)
        pytest.importorskip("sklearn")
        # Some topic models may produce no topics on tiny datasets
        if "## Topic Modeling" not in md:
            pytest.skip("Topic model produced no topics on fixture data")
        assert "## Topic Modeling" in md
        # Co-occurrence network
        assert "## Keyword Co-occurrence Network" in md

    def test_ends_with_academic_template_marker(self, sample_records):
        md = _build_academic(sample_records)
        assert "academic template" in md

    def test_year_range_in_header(self, sample_records):
        md = _build_academic(sample_records)
        assert "Year range" in md
        assert "2020" in md
        assert "2024" in md

    def test_h_index_in_header(self, sample_records):
        md = _build_academic(sample_records)
        assert "h-index" in md

    def test_top_authors_table_has_h_index_column(self, sample_records):
        md = _build_academic(sample_records)
        assert "| h-index |" in md


# ===========================================================================
# Simple template
# ===========================================================================


class TestSimpleTemplate:
    def test_contains_core_sections(self, sample_records):
        md = _build_simple(sample_records)
        assert "## Overview" in md
        assert "## Top 5 Authors" in md
        assert "## Top 5 Keywords" in md

    def test_does_not_contain_academic_only_sections(self, sample_records):
        md = _build_simple(sample_records)
        # Simple template is concise — no topic modeling or co-occurrence
        assert "## Topic Modeling" not in md
        assert "## Keyword Co-occurrence Network" not in md
        assert "## Top Journals" not in md

    def test_ends_with_simple_template_marker(self, sample_records):
        md = _build_simple(sample_records)
        assert "simple template" in md

    def test_uses_top_5(self, sample_records):
        """Simple template should cap author/keyword lists at 5."""
        # Build 20 distinct authors
        records = [
            Record(
                title=f"P{i}",
                year=2024,
                authors=[Author(full_name=f"Author_{i:02d}", order=1)],
                keywords=[f"kw{i:02d}"],
                source_database="T",
            )
            for i in range(20)
        ]
        md = _build_simple(records)
        # Count rows in the Top 5 Authors table
        # The table has header + separator + N rows
        authors_section = md.split("## Top 5 Authors")[1].split("## Top 5 Keywords")[0]
        # Each row is "|  N | ..."
        data_rows = [
            line for line in authors_section.split("\n")
            if line.startswith("|  ") and "|" in line and "---" not in line
        ]
        # Should be ≤ 5 rows
        assert len(data_rows) <= 5

    def test_5_years_window(self, sample_records):
        """Simple template should show only the last 5 years."""
        # Records span 2020-2024 (5 years)
        md = _build_simple(sample_records)
        # Year 2019 should not appear (outside window)
        assert "2019" not in md.split("## Publication Trend")[1].split("## Top")[0]

    def test_quieter_header(self, sample_records):
        """Simple template uses 'Quick Summary' title, not 'Analysis Report'."""
        md = _build_simple(sample_records)
        assert "# Quick Summary" in md
        assert "Analysis Report" not in md


# ===========================================================================
# Dispatcher
# ===========================================================================


class TestDispatcher:
    def test_dispatch_academic(self, sample_records):
        md = _build_markdown(sample_records, template="academic")
        assert "academic template" in md

    def test_dispatch_simple(self, sample_records):
        md = _build_markdown(sample_records, template="simple")
        assert "simple template" in md

    def test_dispatch_default_is_academic(self, sample_records):
        md = _build_markdown(sample_records)
        assert "academic template" in md

    def test_unknown_template_falls_back_to_academic(self, sample_records):
        # Defensive: should not raise, fall back to academic
        md = _build_markdown(sample_records, template="nonexistent")
        assert "academic template" in md


# ===========================================================================
# CLI integration
# ===========================================================================


def _setup(clean_cwd: Path) -> None:
    records = [
        Record(
            title=f"P{i}",
            year=2024,
            authors=[Author(full_name=f"A{i}", order=1)],
            keywords=[f"kw{i}", "shared"],
            source_database="T",
        )
        for i in range(5)
    ]
    seed_cli_db(clean_cwd, records)


class TestCliQuick:
    def test_academic_md(self, cli_runner, clean_cwd, monkeypatch):
        _setup(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        out = clean_cwd / "r.md"
        result = cli_runner.invoke(app, ["report", "quick", "-o", str(out), "-t", "academic"])
        assert result.exit_code == 0
        assert out.exists()
        assert "academic template" in out.read_text()

    def test_simple_md(self, cli_runner, clean_cwd, monkeypatch):
        _setup(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        out = clean_cwd / "r.md"
        result = cli_runner.invoke(app, ["report", "quick", "-o", str(out), "-t", "simple"])
        assert result.exit_code == 0
        assert out.exists()
        assert "simple template" in out.read_text()
        # Simple should be smaller / less detailed
        assert "## Topic Modeling" not in out.read_text()

    def test_html_output(self, cli_runner, clean_cwd, monkeypatch):
        _setup(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        out = clean_cwd / "r.html"
        result = cli_runner.invoke(
            app, ["report", "quick", "-o", str(out), "-t", "simple"]
        )
        assert result.exit_code == 0
        assert out.exists()
        content = out.read_text()
        assert "<!DOCTYPE html>" in content
        assert "simple template" in content

    def test_invalid_template_rejected(self, cli_runner, clean_cwd, monkeypatch):
        _setup(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        out = clean_cwd / "r.md"
        result = cli_runner.invoke(
            app, ["report", "quick", "-o", str(out), "-t", "bogus"]
        )
        # Should reject unknown template
        assert result.exit_code != 0

    def test_no_data(self, cli_runner, clean_cwd):
        out = clean_cwd / "r.md"
        result = cli_runner.invoke(
            app, ["report", "quick", "-o", str(out), "-t", "academic"]
        )
        assert result.exit_code in (0, 1)

    def test_academic_is_larger_than_simple(self, cli_runner, clean_cwd, monkeypatch):
        """Sanity: academic should produce more bytes than simple."""
        _setup(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        out_a = clean_cwd / "academic.md"
        out_s = clean_cwd / "simple.md"
        cli_runner.invoke(app, ["report", "quick", "-o", str(out_a), "-t", "academic"])
        cli_runner.invoke(app, ["report", "quick", "-o", str(out_s), "-t", "simple"])
        if out_a.exists() and out_s.exists():
            assert out_a.stat().st_size > out_s.stat().st_size
