"""Tests for stats.funding (P4-4) — StatsEngine and CLI command."""

from __future__ import annotations

from pathlib import Path

from citationer.analysis.stats import FundingStats, StatsEngine
from citationer.cli.main import app
from citationer.models.record import Author, Record
from tests._factories import make_record
from tests._helpers import seed_cli_db

# ===========================================================================
# StatsEngine.funding (unit)
# ===========================================================================


def _r(
    title: str = "T",
    year: int | None = 2024,
    funding: list[str] | None = None,
) -> Record:
    """Minimal funding test record."""
    return make_record(
        title=title,
        year=year,
        funding=funding,
        authors=[Author(full_name="A", order=1)],
        source_database="T",
    )


class TestFundingEmpty:
    def test_empty_records(self):
        engine = StatsEngine([])
        result = engine.funding()
        assert isinstance(result, FundingStats)
        assert result.funded_count == 0
        assert result.unfunded_count == 0
        assert result.funding_rate == 0.0
        assert result.top_funders.items == []
        assert result.yearly_funded == {}


class TestFundingCounts:
    def test_all_funded(self):
        engine = StatsEngine([_r(funding=["NSF"])] * 5)
        result = engine.funding()
        assert result.funded_count == 5
        assert result.unfunded_count == 0
        assert result.funding_rate == 1.0

    def test_all_unfunded(self):
        engine = StatsEngine([_r(funding=None)] * 5)
        result = engine.funding()
        assert result.funded_count == 0
        assert result.unfunded_count == 5
        assert result.funding_rate == 0.0

    def test_mixed(self):
        records = [_r(funding=["A"])] * 3 + [_r(funding=None)] * 7
        engine = StatsEngine(records)
        result = engine.funding()
        assert result.funded_count == 3
        assert result.unfunded_count == 7
        assert abs(result.funding_rate - 0.3) < 1e-9

    def test_empty_funding_list_counts_as_unfunded(self):
        """An explicit empty list [] should be treated as no funding."""
        engine = StatsEngine([_r(funding=[])])
        result = engine.funding()
        assert result.funded_count == 0
        assert result.unfunded_count == 1


class TestFundingDeduplication:
    def test_same_funder_deduped_per_record(self):
        """Same funder repeated in one record counts once."""
        r = _r(funding=["NSF", "NSF", "NSF"])
        engine = StatsEngine([r])
        result = engine.funding()
        # NSF should count 1 (not 3) for this single record
        assert result.top_funders.items == [("NSF", 1)]

    def test_different_funders_counted_independently(self):
        r = _r(funding=["NSF", "NIH", "MOE"])
        engine = StatsEngine([r])
        result = engine.funding()
        # 3 different funders, each with count 1
        assert len(result.top_funders.items) == 3
        counts = dict(result.top_funders.items)
        assert all(c == 1 for c in counts.values())

    def test_funder_aggregation_across_records(self):
        records = [
            _r(title=f"P{i}", funding=["NSF"]) for i in range(3)
        ] + [_r(title="P4", funding=["NIH"])]
        engine = StatsEngine(records)
        result = engine.funding()
        # NSF in 3 records, NIH in 1
        counts = dict(result.top_funders.items)
        assert counts["NSF"] == 3
        assert counts["NIH"] == 1

    def test_whitespace_only_funder_ignored(self):
        r = _r(funding=["NSF", "   ", "\t"])
        engine = StatsEngine([r])
        result = engine.funding()
        assert result.top_funders.items == [("NSF", 1)]

    def test_total_unique(self):
        records = [
            _r(title=f"P{i}", funding=[f"Funder{i}"]) for i in range(5)
        ]
        engine = StatsEngine(records)
        result = engine.funding()
        assert result.top_funders.total_unique == 5


class TestFundingTopN:
    def test_top_n_limit(self):
        records = [_r(title=f"P{i}", funding=[f"Funder{i}"]) for i in range(10)]
        engine = StatsEngine(records)
        result = engine.funding(top_n=3)
        assert len(result.top_funders.items) == 3

    def test_top_n_default(self):
        records = [_r(title=f"P{i}", funding=[f"Funder{i}"]) for i in range(25)]
        engine = StatsEngine(records)
        result = engine.funding()
        # Default top_n=20
        assert len(result.top_funders.items) == 20

    def test_top_n_sorted_by_count_desc(self):
        records = (
            [_r(title=f"P{i}", funding=["NSF"]) for i in range(5)]
            + [_r(title="P6", funding=["NIH"])]
            + [_r(title="P7", funding=["MOE"])]
        )
        engine = StatsEngine(records)
        result = engine.funding()
        assert result.top_funders.items[0] == ("NSF", 5)


class TestFundingYearly:
    def test_yearly_breakdown(self):
        records = [
            _r(title="P1", year=2020, funding=["NSF"]),
            _r(title="P2", year=2020, funding=["NIH"]),
            _r(title="P3", year=2021, funding=["NSF"]),
            _r(title="P4", year=None, funding=["NSF"]),
        ]
        engine = StatsEngine(records)
        result = engine.funding()
        assert result.yearly_funded[2020] == 2
        assert result.yearly_funded[2021] == 1
        # Records with year=None are still funded but not in yearly breakdown
        assert result.funded_count == 4

    def test_yearly_skips_unfunded(self):
        records = [
            _r(title="P1", year=2020, funding=["NSF"]),
            _r(title="P2", year=2020, funding=None),
        ]
        engine = StatsEngine(records)
        result = engine.funding()
        assert result.yearly_funded[2020] == 1


# ===========================================================================
# CLI: stats funding
# ===========================================================================


def _setup_data(clean_cwd: Path) -> None:
    """Setup DB with records exercising funding analysis."""
    records = [
        Record(
            title="Funded 1",
            year=2024,
            authors=[Author(full_name="A", order=1)],
            funding=["National Science Foundation"],
            source_database="WoS",
        ),
        Record(
            title="Funded 2",
            year=2024,
            authors=[Author(full_name="B", order=1)],
            funding=["National Science Foundation", "NIH R01"],
            source_database="WoS",
        ),
        Record(
            title="Funded 3",
            year=2023,
            authors=[Author(full_name="C", order=1)],
            funding=["National Key R&D"],
            source_database="CNKI",
        ),
        Record(
            title="Unfunded",
            year=2024,
            authors=[Author(full_name="D", order=1)],
            funding=None,
            source_database="Scopus",
        ),
        Record(
            title="Unfunded 2",
            year=2023,
            authors=[Author(full_name="E", order=1)],
            funding=[],
            source_database="Scopus",
        ),
    ]
    seed_cli_db(clean_cwd, records)


class TestFundingCommand:
    def test_funding_command(self, cli_runner, clean_cwd, monkeypatch):
        _setup_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["stats", "funding"])
        assert result.exit_code == 0, f"Output: {result.output}"
        # Should show funding overview
        assert "资助" in result.output or "基金" in result.output

    def test_funding_top_n(self, cli_runner, clean_cwd, monkeypatch):
        _setup_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["stats", "funding", "--top", "5"])
        assert result.exit_code == 0

    def test_funding_no_data(self, cli_runner, clean_cwd):
        result = cli_runner.invoke(app, ["stats", "funding"])
        assert result.exit_code in (0, 1)

    def test_funding_help(self, cli_runner):
        result = cli_runner.invoke(app, ["stats", "funding", "--help"])
        assert "funding" in result.output.lower() or "基金" in result.output

    def test_funding_shows_rate(self, cli_runner, clean_cwd, monkeypatch):
        _setup_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["stats", "funding"])
        assert result.exit_code == 0
        # 3 funded / 5 total = 60%
        assert "60" in result.output or "资助率" in result.output
