"""Regression tests for v4.6.5 bug fixes (issues #25-#31 + review #6)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from citationer.analysis.dedup import (
    _title_similarity,
)
from citationer.analysis.trend import TrendEngine
from citationer.cli.main import app
from citationer.models.record import Author, Record
from citationer.utils.database import CitationDatabase
from citationer.utils.serialization import record_to_db_serializable


def _r(title: str = "T", year: int | None = 2024, journal: str = "Nature") -> Record:
    return Record(
        title=title,
        year=year,
        journal=journal,
        authors=[Author(full_name="A", order=1)],
        keywords=["x"],
        source_database="T",
    )


# ===========================================================================
# BUG-012: report HTML suffix case sensitivity
# ===========================================================================


class TestBug012HtmlSuffix:
    def test_uppercase_html_recognized(self, tmp_path):
        """report.HTML (uppercase) should be treated as HTML output."""

        # _md_to_html always produces HTML — the case-sensitivity bug
        # is in the dispatch at quick() (output.suffix == ".html").
        # We check the dispatch logic indirectly: the function uses
        # output.suffix.lower() now.
        from citationer.cli import report_cmd as rc

        source = open(rc.__file__).read()
        assert 'output.suffix.lower() == ".html"' in source, (
            "report_cmd.quick() must use suffix.lower() for HTML dispatch"
        )

    def test_uppercase_md_recognized(self):
        """report.MD (uppercase) should also work as Markdown."""
        from citationer.cli import report_cmd as rc

        source = open(rc.__file__).read()
        # The HTML branch uses .lower(); the else branch handles everything
        # else as Markdown.  So .MD falls into Markdown by default.
        assert "else:\n        output.write_text(md" in source or (
            "else:\n        output.write_text(md, encoding" in source
        )


# ===========================================================================
# BUG-013: clean --save works even when no duplicates
# ===========================================================================


def _setup_db(clean_cwd: Path, records: list[Record]) -> None:
    db_dir = clean_cwd / ".citationer"
    db_dir.mkdir(exist_ok=True)
    db = CitationDatabase(db_dir / "cache.db")
    db.initialize()
    for r in records:
        payload = record_to_db_serializable(r)
        db.insert_record(
            record_data=payload["record_data"],
            authors=payload["authors"],
            keywords=payload["keywords"],
            institutions=payload["institutions"],
        )
    db.close()


class TestBug013CleanSave:
    def test_save_works_with_no_duplicates(self, cli_runner, clean_cwd, monkeypatch):
        """--save should create CSV even when no duplicates are detected."""
        records = [
            _r(title="Unique 1", year=2024),
            _r(title="Unique 2", year=2024),
        ]
        _setup_db(clean_cwd, records)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["clean", "--save"])
        assert result.exit_code == 0
        # BUG-013 fix: CSV is created regardless of dup count
        assert (clean_cwd / "output" / "cls" / "cleaned_records.csv").exists()

    def test_save_works_with_duplicates(self, cli_runner, clean_cwd, monkeypatch):
        """--save still works when duplicates are merged (regression)."""
        records = [
            _r(title="Duplicate Paper", year=2024),
            _r(title="Duplicate Paper", year=2024),  # exact match
        ]
        _setup_db(clean_cwd, records)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["clean", "--save"])
        assert result.exit_code == 0
        assert (clean_cwd / "output" / "cls" / "cleaned_records.csv").exists()


# ===========================================================================
# BUG-008: trend.river no longer drops trailing window
# ===========================================================================


class TestBug008RiverTrailingWindow:
    def test_river_includes_trailing_year(self):
        """7 years of data with window=5 must produce 2 windows (not 1)."""
        records = []
        for y in range(2014, 2021):  # 2014..2020 = 7 years
            for _ in range(2):
                records.append(_r(title=f"P{y}", year=y, journal="X"))
        engine = TrendEngine(records)
        result = engine.river(top_n=3, window=5)
        # Pre-fix: only one window "2014-2018"
        # Post-fix: two windows "2014-2018" and "2019-2020"
        assert len(result.windows) == 2
        assert result.windows[0] == "2014-2018"
        assert result.windows[1] == "2019-2020"

    def test_river_exact_multiple(self):
        """12 years / 3 = exactly 4 windows (no partial)."""
        records = []
        for y in range(2010, 2022):  # 12 years
            records.append(_r(title=f"P{y}", year=y, journal="X"))
        engine = TrendEngine(records)
        result = engine.river(top_n=3, window=3)
        assert len(result.windows) == 4
        assert result.windows == ["2010-2012", "2013-2015", "2016-2018", "2019-2021"]


# ===========================================================================
# BUG-009: dedup _title_similarity now short-circuits
# ===========================================================================


class TestBug009TitleSimilarityThreshold:
    def test_threshold_accepted_no_crash(self):
        """_title_similarity now actually uses the threshold argument.

        The threshold was previously accepted but ignored.  After the
        fix, calls with various thresholds don't crash and return values
        consistent with the actual string similarity.
        """
        t1 = "Completely Different Title About Cats"
        t2 = "Another Random Title About Dogs And Horses"
        # Threshold should be accepted; result depends on rapidfuzz
        # score_cutoff behaviour.  Just ensure the call succeeds.
        result = _title_similarity(t1, t2, threshold=0.99)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_zero_threshold_returns_full_score(self):
        t1 = "Hello World"
        t2 = "Hello World"
        result = _title_similarity(t1, t2, threshold=0.0)
        assert result >= 0.99

    def test_threshold_does_not_change_high_similarity(self):
        """For similar titles, the result should be high regardless of
        threshold (as long as threshold <= similarity)."""
        t1 = "Machine Learning in Healthcare"
        t2 = "Machine Learning in Healthcare"
        # Threshold lower than actual similarity → returns full score
        result = _title_similarity(t1, t2, threshold=0.5)
        assert result >= 0.99


# ===========================================================================
# BUG-010: run pipeline sets results[name] = None on failure
# ===========================================================================


def test_bug010_results_marked_none_on_failure(tmp_path, monkeypatch):
    """When a step fails, its name is still added to results as None."""
    pipeline = tmp_path / "p.yaml"
    pipeline.write_text(
        "name: failure_test\n"
        "steps:\n"
        "  - name: bad_step\n"
        "    action: stats\n"
        "    type: invalid_type\n"  # ValueError
    )
    # Need data for the pipeline to load
    db_dir = tmp_path / ".citationer"
    db_dir.mkdir(exist_ok=True)
    db = CitationDatabase(db_dir / "cache.db")
    db.initialize()
    payload = record_to_db_serializable(_r())
    db.insert_record(
        record_data=payload["record_data"],
        authors=payload["authors"],
        keywords=payload["keywords"],
        institutions=payload["institutions"],
    )
    db.close()
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["run", str(pipeline)])
    # on_error default is continue; exit 0
    assert result.exit_code == 0
    # Output should mention None
    assert "bad_step" in result.output
    # The fix ensures no KeyError from later refs
    assert "KeyError" not in result.output


# ===========================================================================
# BUG-011: LLM enhancement error surfaces
# ===========================================================================


def test_bug011_llm_error_surfaced(monkeypatch, tmp_path):
    """When LLM enhancement fails, the user sees an error message."""
    # Set up a DB and run report quick --enhance
    db_dir = tmp_path / ".citationer"
    db_dir.mkdir(exist_ok=True)
    db = CitationDatabase(db_dir / "cache.db")
    db.initialize()
    payload = record_to_db_serializable(_r())
    db.insert_record(
        record_data=payload["record_data"],
        authors=payload["authors"],
        keywords=payload["keywords"],
        institutions=payload["institutions"],
    )
    db.close()

    # Force LLMClient.query to raise
    import citationer.llm.client as llm_client_mod

    class _BoomClient:
        def __init__(self, *a, **kw):
            pass
        def query(self, *a, **kw):
            raise RuntimeError("simulated LLM outage")

    monkeypatch.setattr(llm_client_mod, "LLMClient", _BoomClient)
    # Provide API key so it tries to instantiate
    monkeypatch.setenv("CITATIONER_LLM_API_KEY", "sk-fake")

    monkeypatch.chdir(tmp_path)
    out = tmp_path / "r.md"
    runner = CliRunner()
    result = runner.invoke(app, ["report", "quick", "-o", str(out), "--enhance"])
    # Exit 0 (enhancement failure is non-fatal), but error is reported
    assert result.exit_code == 0
    assert "LLM 增强失败" in result.output or "simulated LLM outage" in result.output


# ===========================================================================
# BUG-014: trend.strategy no longer recomputes top_kw/keywords
# ===========================================================================


class TestBug014StrategyCache:
    def test_strategy_single_pass(self):
        """strategy() should not have a second recompute loop for top_kw/keywords."""
        from citationer.analysis import trend as trend_mod

        source = open(trend_mod.__file__).read()
        # After fix, the second loop should iterate over cluster_stats
        # and unpack (cluster, centrality, density, top_kw, keywords).
        assert "for cluster, centrality, density, top_kw, keywords" in source, (
            "strategy() should iterate over cluster_stats with 5-tuple"
        )
        # The old comment "# Recompute (we lost the computed values in the
        # loop above)" should be gone.
        assert "Recompute (we lost the computed values" not in source, (
            "Old dead-code comment should be removed after BUG-014 fix"
        )
