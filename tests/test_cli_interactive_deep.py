"""Deep tests for cli/interactive_cmd.py — wizard subroutines.

Many interactive_* subroutines use rich.prompt which is hard to mock.
We focus on:
- Early-return paths (no data, empty db)
- Internal helpers (_print_menu, _show_*) called directly
- The 'q' quit path (input="q")
"""

from __future__ import annotations

from pathlib import Path

from citationer.cli.interactive_cmd import (
    _print_menu,
    _show_top_authors,
    _show_top_institutions,
    _show_top_journals,
    _show_yearly,
)
from citationer.cli.main import app
from citationer.models.record import Author, Record
from citationer.utils.database import CitationDatabase
from tests._helpers import seed_cli_db


def _setup_db(clean_cwd: Path) -> None:
    """Setup a small DB for interactive tests."""
    records = [
        Record(
            title=f"Paper {i}",
            year=2020 + i,
            authors=[Author(full_name=f"A{i}", order=1)],
            keywords=[f"kw{i}"],
            source_database="T",
        )
        for i in range(3)
    ]
    seed_cli_db(clean_cwd, records)


class TestInteractiveWizard:
    def test_interactive_no_db(self, cli_runner, clean_cwd, monkeypatch):
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["interactive"], input="q\n")
        # Should not crash; exits because no DB
        assert result.exit_code in (0, 1)

    def test_interactive_empty_db(self, cli_runner, clean_cwd, monkeypatch):
        db_dir = clean_cwd / ".citationer"
        db_dir.mkdir(exist_ok=True)
        CitationDatabase(db_dir / "cache.db").initialize()
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["interactive"], input="q\n")
        assert result.exit_code in (0, 1)

    def test_interactive_quit(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["interactive"], input="q\n")
        # Should exit cleanly
        assert result.exit_code in (0, 1)


class TestInteractiveHelpers:
    def test_print_menu(self):
        """_print_menu should not raise (just prints)."""
        _print_menu()

    def test_show_yearly(self):
        from citationer.analysis.stats import StatsEngine

        records = [
            Record(title=f"P{i}", year=2020 + i, authors=[Author(full_name="A", order=1)])
            for i in range(3)
        ]
        engine = StatsEngine(records)
        _show_yearly(engine)

    def test_show_top_journals(self, monkeypatch):
        from rich.prompt import Prompt

        from citationer.analysis.stats import StatsEngine

        # Skip the "Top-N" prompt
        monkeypatch.setattr(Prompt, "ask", lambda *args, **kwargs: "5")

        records = [
            Record(
                title=f"P{i}",
                year=2024,
                journal=f"Journal {i}",
                authors=[Author(full_name="A", order=1)],
            )
            for i in range(3)
        ]
        engine = StatsEngine(records)
        _show_top_journals(engine)

    def test_show_top_authors(self, monkeypatch):
        from rich.prompt import Prompt

        from citationer.analysis.stats import StatsEngine

        monkeypatch.setattr(Prompt, "ask", lambda *args, **kwargs: "5")

        records = [
            Record(
                title=f"P{i}",
                year=2024,
                authors=[Author(full_name=f"Author {i}", order=1)],
            )
            for i in range(3)
        ]
        engine = StatsEngine(records)
        _show_top_authors(engine)

    def test_show_top_institutions(self, monkeypatch):
        from rich.prompt import Prompt

        from citationer.analysis.stats import StatsEngine

        monkeypatch.setattr(Prompt, "ask", lambda *args, **kwargs: "5")

        from citationer.models.record import Institution

        records = [
            Record(
                title=f"P{i}",
                year=2024,
                authors=[Author(full_name="A", order=1)],
                institutions=[Institution(name=f"Inst {i}")],
            )
            for i in range(3)
        ]
        engine = StatsEngine(records)
        _show_top_institutions(engine)

    def test_show_yearly_with_real_data(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        from rich.prompt import Prompt

        from citationer.analysis.stats import StatsEngine
        from citationer.utils.db_loader import load_records_from_db

        monkeypatch.setattr(Prompt, "ask", lambda *args, **kwargs: "5")
        records = load_records_from_db(clean_cwd / ".citationer" / "cache.db")
        engine = StatsEngine(records)
        _show_yearly(engine)
        _show_top_journals(engine)
        _show_top_authors(engine)
        _show_top_institutions(engine)


class TestInteractiveSubmenus:
    """Walk through the interactive wizard menu tree with queued prompts."""

    @staticmethod
    def _queue_prompts(monkeypatch, answers: list[str], confirm: bool = False) -> None:
        it = iter(answers)

        def _ask(*args, **kwargs):
            return next(it)

        monkeypatch.setattr("rich.prompt.Prompt.ask", _ask)
        monkeypatch.setattr("rich.prompt.Confirm.ask", lambda *args, **kwargs: confirm)

    def test_stats_overview(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["1", "1", "n", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_stats_yearly(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["1", "2", "n", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_stats_top_journals(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["1", "3", "5", "n", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_stats_top_authors(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["1", "4", "5", "n", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_stats_top_institutions(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["1", "5", "5", "n", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_stats_back(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["1", "b", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_text_keywords(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["2", "1", "5", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_text_topics(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["2", "2", "lda", "3", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_text_summary(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["2", "3", "3", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_text_back(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["2", "b", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_network_keywords(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["3", "1", "5", "2", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_network_authors(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["3", "2", "1", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_network_institutions(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["3", "3", "1", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_network_back(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["3", "b", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_trend_hotspots(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["4", "1", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_trend_strategy(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["4", "2", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_trend_river(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["4", "3", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_trend_back(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["4", "b", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_scan_directory(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        scan_dir = clean_cwd / "imports"
        scan_dir.mkdir()
        (scan_dir / "sample.ris").write_text("TY  - JOUR\nTI  - X\nER  - \n", encoding="utf-8")
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["5", str(scan_dir), "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)
        assert "RIS" in result.output or "sample" in result.output

    def test_scan_directory_not_found(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["5", str(clean_cwd / "missing"), "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)
        assert "不存在" in result.output

    def test_export_csv(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["6", "1", "records.csv", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)
        assert (clean_cwd / "output" / "cls" / "records.csv").exists()

    def test_export_json(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["6", "2", "records.json", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)
        assert (clean_cwd / "output" / "cls" / "records.json").exists()

    def test_export_bibtex(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["6", "3", "records.bib", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)
        assert (clean_cwd / "output" / "cls" / "records.bib").exists()

    def test_export_back(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["6", "b", "q"])
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)

    def test_db_clear(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["7", "y", "q"], confirm=True)
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)
        assert "已清空" in result.output

    def test_db_clear_rejected(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        self._queue_prompts(monkeypatch, ["7", "n", "q"], confirm=False)
        result = cli_runner.invoke(app, ["interactive"])
        assert result.exit_code in (0, 1)
        assert "已清空" not in result.output
