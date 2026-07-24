"""Tests for P4-6 — interactive mode save_report functionality."""

from __future__ import annotations

import pytest

from citationer.cli.interactive_cmd import save_interactive_report
from citationer.models.record import Author, Record
from tests._factories import make_record


def _r(title: str = "T", year: int = 2024) -> Record:
    """Minimal interactive-save test record."""
    return make_record(
        title=title,
        year=year,
        journal="Nature",
        authors=[Author(full_name="A", order=1)],
        keywords=["ml"],
        source_database="T",
    )


@pytest.fixture
def sample_records() -> list[Record]:
    return [_r(f"P{i}") for i in range(3)]


# ===========================================================================
# save_interactive_report — unit tests
# ===========================================================================


class TestSaveMarkdown:
    def test_save_with_filename(self, sample_records, tmp_path):
        out = tmp_path / "report.md"
        result = save_interactive_report(sample_records, str(out))
        assert result == out
        assert out.exists()
        content = out.read_text()
        assert "## Overview" in content

    def test_save_default_template_academic(self, sample_records, tmp_path):
        out = tmp_path / "r.md"
        save_interactive_report(sample_records, str(out))
        assert "academic template" in out.read_text()

    def test_save_simple_template(self, sample_records, tmp_path):
        out = tmp_path / "r.md"
        save_interactive_report(sample_records, str(out), template="simple")
        content = out.read_text()
        assert "simple template" in content
        assert "Quick Summary" in content


class TestSaveHtml:
    def test_html_extension(self, sample_records, tmp_path):
        out = tmp_path / "report.html"
        result = save_interactive_report(sample_records, str(out))
        assert result == out
        assert out.exists()
        content = out.read_text()
        assert "<!DOCTYPE html>" in content
        assert "academic template" in content

    def test_html_simple(self, sample_records, tmp_path):
        out = tmp_path / "r.html"
        save_interactive_report(sample_records, str(out), template="simple")
        content = out.read_text()
        assert "simple template" in content
        assert "<!DOCTYPE html>" in content


class TestSavePathResolution:
    def test_bare_filename_uses_output_report_dir(self, sample_records, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = save_interactive_report(sample_records, "my_report.md")
        assert result is not None
        assert result.exists()
        # Should be under output/report/
        assert "output" in str(result)
        assert "report" in str(result)
        assert result.name == "my_report.md"

    def test_absolute_path_preserved(self, sample_records, tmp_path):
        out = tmp_path / "absolute.md"
        result = save_interactive_report(sample_records, str(out))
        assert result == out
        assert out.exists()

    def test_relative_subdir_path_preserved(self, sample_records, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Relative path with subdir (not bare) should be preserved
        result = save_interactive_report(sample_records, "subdir/r.md")
        assert result is not None
        assert result.exists()


class TestSaveErrorHandling:
    def test_invalid_template_falls_back(self, sample_records, tmp_path):
        """Unknown template should not raise (falls back to academic)."""
        out = tmp_path / "r.md"
        result = save_interactive_report(
            sample_records, str(out), template="nonexistent"
        )
        assert result is not None
        assert out.exists()
        # Falls back to academic
        assert "academic template" in out.read_text()

    def test_empty_records(self, tmp_path):
        """Empty record list should still produce a valid (empty) report."""
        out = tmp_path / "r.md"
        result = save_interactive_report([], str(out))
        assert result == out
        assert out.exists()
        # No crash on empty input
        content = out.read_text()
        assert "Total records" in content
        assert "| 0 |" in content or "0 records" in content


class TestSaveReusesReportEngine:
    """Verify interactive save uses the same engine as `report quick`."""

    def test_same_as_report_quick_academic(self, sample_records, tmp_path):
        from citationer.cli.report_cmd import _build_markdown

        out = tmp_path / "via_interactive.md"
        out_quick = tmp_path / "via_quick.md"

        save_interactive_report(sample_records, str(out), template="academic")
        out_quick.write_text(_build_markdown(sample_records, template="academic"), encoding="utf-8")

        assert out.read_text() == out_quick.read_text()

    def test_same_as_report_quick_simple(self, sample_records, tmp_path):
        from citationer.cli.report_cmd import _build_markdown

        out = tmp_path / "via_interactive.md"
        out_quick = tmp_path / "via_quick.md"

        save_interactive_report(sample_records, str(out), template="simple")
        out_quick.write_text(_build_markdown(sample_records, template="simple"), encoding="utf-8")

        assert out.read_text() == out_quick.read_text()
