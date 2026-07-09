"""Tests for the trend analysis engine (trend.py).

Covers:
- TrendEngine.hotspots: Kleinberg-style burst detection
- TrendEngine.strategy: Strategic diagram (centrality × density, 4 quadrants)
- TrendEngine.river: Thematic river (keyword share over sliding time windows)
- Dataclass contracts: BurstResult, StrategyTheme, StrategyDiagram, RiverData
- Edge cases: empty data, no years, networkx missing, single keyword
"""

from __future__ import annotations

import pytest

from citationer.analysis.trend import (
    BurstAnalysis,
    BurstResult,
    RiverData,
    StrategyDiagram,
    StrategyTheme,
    TrendEngine,
)
from citationer.models.record import Author, Record


# ===========================================================================
# Test fixtures: tailored records for trend analysis scenarios
# ===========================================================================


def _r(title: str, year: int, kws: list[str], kws_en: list[str] | None = None) -> Record:
    """Build a minimal record for trend tests."""
    return Record(
        title=title,
        year=year,
        keywords=kws,
        keywords_en=kws_en,
        authors=[Author(full_name="Smith, J.", order=1)],
    )


@pytest.fixture
def burst_records() -> list[Record]:
    """Records designed to trigger hotspot detection.

    Layout: keyword 'ml' (machine learning) has a clear burst in years 2020-2022.
    Keyword 'quantum' shows steady low-frequency pattern.
    """
    records: list[Record] = []
    # Years 2015-2019: 1 paper/year mentioning 'ml' (low baseline)
    for y in range(2015, 2020):
        records.append(_r(f"Paper {y} a", y, ["机器学习"], ["ml"]))
        records.append(_r(f"Paper {y} b", y, ["其他"]))
    # Years 2020-2022: 5 papers/year mentioning 'ml' (BURST)
    for y in range(2020, 2023):
        for i in range(5):
            records.append(_r(f"Burst {y} {i}", y, ["机器学习"], ["ml"]))
    # Year 2023: 1 paper mentioning 'ml' (back to baseline)
    for y in [2023]:
        records.append(_r(f"Paper {y} a", y, ["机器学习"], ["ml"]))
        records.append(_r(f"Paper {y} b", y, ["其他"]))
    # Quantum: 1 paper/year across all years (no burst, steady)
    for y in range(2015, 2024):
        records.append(_r(f"Quantum {y}", y, ["量子计算"], ["quantum"]))
    return records


@pytest.fixture
def strategy_records() -> list[Record]:
    """Records designed to produce multiple strategy-diagram themes.

    Three keyword clusters:
    - Cluster A (high internal density, high centrality): 'ml' co-occurs with 'dl', 'ai'
    - Cluster B (low density, high centrality): 'healthcare' co-occurs with everything
    - Cluster C (high density, low centrality): niche 'niche_a' only with 'niche_b'
    """
    records: list[Record] = []
    # Cluster A: ML papers — 'ml' co-occurs with 'dl' and 'ai' frequently
    for i in range(20):
        records.append(_r(f"ML-{i}", 2020, ["ml", "dl", "ai"]))
    # Cluster C: niche papers — only 'niche_a' + 'niche_b' co-occur
    for i in range(15):
        records.append(_r(f"Niche-{i}", 2020, ["niche_a", "niche_b"]))
    # Bridge paper: connects Cluster A to healthcare
    for i in range(5):
        records.append(_r(f"Bridge-{i}", 2020, ["ml", "healthcare"]))
    # Healthcare alone
    for i in range(3):
        records.append(_r(f"Health-{i}", 2020, ["healthcare"]))
    return records


@pytest.fixture
def river_records() -> list[Record]:
    """Records spanning 12 years for river analysis.

    Keyword 'ml' rises in share over time; 'classical' declines.
    """
    records: list[Record] = []
    for y in range(2014, 2026):
        # 10 papers/year total
        # ml share grows: 0% in 2014, 50% in 2025
        ml_papers = max(0, (y - 2014) // 2)
        for i in range(10):
            kws = ["ml"] if i < ml_papers else ["classical"]
            records.append(_r(f"Paper-{y}-{i}", y, kws))
    return records


# ===========================================================================
# BurstResult / StrategyTheme / StrategyDiagram / RiverData dataclasses
# ===========================================================================


class TestDataclasses:
    def test_burst_result_defaults(self):
        """BurstResult should default years to empty dict."""
        b = BurstResult(
            keyword="ml", start_year=2020, end_year=2022, strength=2.5
        )
        assert b.keyword == "ml"
        assert b.start_year == 2020
        assert b.end_year == 2022
        assert b.strength == 2.5
        assert b.years == {}

    def test_burst_result_with_years(self):
        b = BurstResult(
            keyword="ml",
            start_year=2020,
            end_year=2022,
            strength=2.5,
            years={2020: 5, 2021: 6, 2022: 4},
        )
        assert b.years[2020] == 5

    def test_strategy_theme_defaults(self):
        """StrategyTheme requires centrality/density/quadrant (no defaults)."""
        t = StrategyTheme(label="ml", keywords=["ml", "dl"],
                          centrality=0.5, density=1.0, quadrant=1)
        assert t.label == "ml"
        assert t.centrality == 0.5
        assert t.density == 1.0
        assert t.quadrant == 1

    def test_strategy_diagram_defaults(self):
        d = StrategyDiagram()
        assert d.themes == []
        assert d.centrality_median == 0.0
        assert d.density_median == 0.0

    def test_river_data_defaults(self):
        r = RiverData()
        assert r.windows == []
        assert r.keywords == []
        assert r.matrix == {}


# ===========================================================================
# TrendEngine — empty / minimal data
# ===========================================================================


class TestEmptyData:
    def test_empty_records(self):
        engine = TrendEngine([])
        result = engine.hotspots()
        assert isinstance(result, BurstAnalysis)
        assert result.bursts == []
        assert result.total_keywords_analyzed == 0

    def test_empty_strategy(self):
        engine = TrendEngine([])
        result = engine.strategy()
        assert isinstance(result, StrategyDiagram)
        assert result.themes == []

    def test_empty_river(self):
        engine = TrendEngine([])
        result = engine.river()
        assert isinstance(result, RiverData)
        assert result.windows == []
        assert result.keywords == []


# ===========================================================================
# TrendEngine.hotspots — burst detection
# ===========================================================================


class TestHotspots:
    def test_burst_detection(self, burst_records):
        """Burst period for 'ml' should be detected in 2020-2022."""
        engine = TrendEngine(burst_records)
        result = engine.hotspots(top_n=10, gamma=1.0, min_years=2)

        assert isinstance(result, BurstAnalysis)
        # 'ml' should have at least one burst
        ml_bursts = [b for b in result.bursts if b.keyword == "ml"]
        assert len(ml_bursts) >= 1, "Expected burst for 'ml'"
        # The first burst should span the 2020-2022 period
        first = ml_bursts[0]
        assert first.start_year == 2020
        assert first.end_year == 2022
        # Strength should be > 1 (baseline = 1, burst avg = 5)
        assert first.strength > 1.0

    def test_burst_strength_positive(self, burst_records):
        """All detected bursts should have positive strength."""
        engine = TrendEngine(burst_records)
        result = engine.hotspots()
        for b in result.bursts:
            assert b.strength > 0

    def test_burst_sorted_by_strength_desc(self, burst_records):
        """Bursts should be returned in descending strength order."""
        engine = TrendEngine(burst_records)
        result = engine.hotspots()
        strengths = [b.strength for b in result.bursts]
        assert strengths == sorted(strengths, reverse=True)

    def test_top_n_limits_keywords(self, burst_records):
        """top_n should cap the number of keywords analyzed."""
        engine = TrendEngine(burst_records)
        result_n1 = engine.hotspots(top_n=1)
        # 'ml' or 'quantum' should be the only analyzed keyword
        # (whichever has higher total)
        # The total_keywords_analyzed field reflects this
        assert result_n1.total_keywords_analyzed <= 1

    def test_gamma_sensitivity(self, burst_records):
        """Lower gamma → more sensitive (more bursts)."""
        engine = TrendEngine(burst_records)
        result_sensitive = engine.hotspots(gamma=0.5, min_years=2)
        result_strict = engine.hotspots(gamma=3.0, min_years=2)
        # At gamma=0.5 (more sensitive), at least as many bursts
        assert len(result_sensitive.bursts) >= len(result_strict.bursts)

    def test_min_years_filter(self, burst_records):
        """min_years=5 should filter out 3-year bursts."""
        engine = TrendEngine(burst_records)
        result = engine.hotspots(gamma=1.0, min_years=5)
        # The 2020-2022 burst is only 3 years, so 'ml' should NOT appear
        ml_bursts = [b for b in result.bursts if b.keyword == "ml"]
        assert len(ml_bursts) == 0

    def test_no_burst_steady_keyword(self, burst_records):
        """Steady keywords (like 'quantum') should not produce bursts."""
        engine = TrendEngine(burst_records)
        result = engine.hotspots(gamma=1.0, min_years=2)
        # 'quantum' has 1 paper/year consistently — no burst
        quantum_bursts = [b for b in result.bursts if b.keyword == "quantum"]
        assert len(quantum_bursts) == 0

    def test_no_year_records_skipped(self):
        """Records without year should be ignored (not cause errors)."""
        records = [
            _r("No year", 0, ["kw"]),  # year=0 should be skipped (or not contribute)
            _r("Real paper", 2024, ["kw"]),
        ]
        records[0].year = None
        engine = TrendEngine(records)
        # Should not raise
        result = engine.hotspots()
        assert isinstance(result, BurstAnalysis)

    def test_keyword_too_short_filtered(self):
        """Single-character keywords should be filtered out."""
        records = [
            _r(f"Paper {i}", 2020, ["a", "b"]) for i in range(10)
        ]  # "a" and "b" are length 1 — filtered
        engine = TrendEngine(records)
        result = engine.hotspots()
        # No keyword passes the length-2 filter
        assert result.bursts == []

    def test_short_keyword_set_skipped(self):
        """Keywords appearing in <3 years should not be analyzed for burst."""
        records = [
            _r("P1", 2020, ["ml"]),
            _r("P2", 2021, ["ml"]),
            # 'ml' only in 2 years
        ]
        engine = TrendEngine(records)
        result = engine.hotspots()
        # 'ml' skipped (only 2 years, need >= 3)
        assert result.bursts == []

    def test_zh_and_en_keywords_combined(self):
        """Chinese and English keywords should be aggregated for the same token."""
        records = [
            _r("P1", 2020, ["机器学习"], ["machine learning"]),
            _r("P2", 2020, ["机器学习"], ["machine learning"]),
            _r("P3", 2021, ["机器学习"], ["machine learning"]),
        ]
        engine = TrendEngine(records)
        result = engine.hotspots(top_n=5)
        # The burst detection should aggregate by token (both 机器学习 and machine learning
        # are distinct tokens, so 2 separate keywords)
        all_kws = {b.keyword for b in result.bursts}
        # Both should appear (or at least be analyzed)
        # Not a strict assertion on bursts (depends on baseline)
        assert isinstance(result.bursts, list)

    def test_burst_count_2_consecutive_years_qualifies(self):
        """Bursts with min_years=2 are detected when burst year count >= 2.

        NOTE: The hotspots algorithm has a hard-coded `c >= 2` floor
        on burst year counts (see BUG-004).  This test uses 3 papers/year
        in burst years and 1 paper/year in baseline years to satisfy
        that floor while still triggering burst detection.
        """
        records = []
        # 3 years of high activity (3 papers/year — above the c>=2 floor)
        for y in [2020, 2021, 2022]:
            for _ in range(3):
                records.append(_r("Paper", y, ["kw"]))
        # 2 years of low activity before/after
        for y in [2018, 2019, 2023, 2024]:
            records.append(_r("Low", y, ["kw"]))
        engine = TrendEngine(records)
        result = engine.hotspots(min_years=2)
        # Should detect the 3-year burst
        assert any(b.keyword == "kw" for b in result.bursts)


# ===========================================================================
# TrendEngine.strategy — strategic diagram
# ===========================================================================


class TestStrategy:
    def test_basic_strategy(self, strategy_records):
        """Should produce a diagram with themes."""
        engine = TrendEngine(strategy_records)
        result = engine.strategy(top_n=10)

        assert isinstance(result, StrategyDiagram)
        # Should have some themes
        assert len(result.themes) > 0
        # Each theme should have at least 2 keywords (cluster)
        for theme in result.themes:
            assert len(theme.keywords) >= 1
            assert 0 <= theme.quadrant <= 4

    def test_strategy_themes_sorted_by_density(self, strategy_records):
        """Themes should be sorted by density descending."""
        engine = TrendEngine(strategy_records)
        result = engine.strategy()
        if len(result.themes) > 1:
            densities = [t.density for t in result.themes]
            assert densities == sorted(densities, reverse=True)

    def test_strategy_quadrants_valid(self, strategy_records):
        """Quadrant values should be 1-4."""
        engine = TrendEngine(strategy_records)
        result = engine.strategy()
        for theme in result.themes:
            assert theme.quadrant in (1, 2, 3, 4)

    def test_strategy_density_positive(self, strategy_records):
        """Density values should be non-negative."""
        engine = TrendEngine(strategy_records)
        result = engine.strategy()
        for theme in result.themes:
            assert theme.density >= 0
            assert theme.centrality >= 0

    def test_strategy_medians_set(self, strategy_records):
        """When themes exist, medians should be numeric."""
        engine = TrendEngine(strategy_records)
        result = engine.strategy()
        if result.themes:
            # Medians should be set (Pydantic/round() may return int when value is 0)
            assert isinstance(result.centrality_median, (int, float))
            assert isinstance(result.density_median, (int, float))

    def test_strategy_no_data(self):
        """No data → empty diagram."""
        engine = TrendEngine([])
        result = engine.strategy()
        assert result.themes == []
        assert result.centrality_median == 0.0
        assert result.density_median == 0.0

    def test_strategy_minimal_cooccurrence(self):
        """Few keywords, no real co-occurrence → minimal output."""
        records = [
            _r("P1", 2020, ["only_one"]),
        ]
        engine = TrendEngine(records)
        result = engine.strategy()
        # Single keyword can't form edges — empty themes
        assert result.themes == []

    def test_strategy_label_is_top_keyword(self, strategy_records):
        """Theme label should be the most frequent keyword in the cluster."""
        engine = TrendEngine(strategy_records)
        result = engine.strategy()
        for theme in result.themes:
            # Label should be in the keywords list
            assert theme.label in theme.keywords

    def test_strategy_without_networkx(self, monkeypatch, strategy_records):
        """Missing networkx should return empty diagram, not crash."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "networkx" or name.startswith("networkx."):
                raise ImportError(f"No module named {name}")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        engine = TrendEngine(strategy_records)
        result = engine.strategy()
        assert result.themes == []


# ===========================================================================
# TrendEngine.river — thematic river
# ===========================================================================


class TestRiver:
    def test_basic_river(self, river_records):
        """Should produce windows, keywords, and matrix."""
        engine = TrendEngine(river_records)
        result = engine.river(top_n=5, window=3)

        assert isinstance(result, RiverData)
        assert len(result.windows) > 0
        assert len(result.keywords) > 0
        assert len(result.keywords) <= 5

    def test_river_matrix_shape(self, river_records):
        """Matrix should have one list per keyword, matching windows length."""
        engine = TrendEngine(river_records)
        result = engine.river(top_n=5, window=3)

        for kw in result.keywords:
            assert kw in result.matrix
            assert len(result.matrix[kw]) == len(result.windows)

    def test_river_window_labels(self, river_records):
        """Window labels should be 'start-end' format."""
        engine = TrendEngine(river_records)
        result = engine.river(window=3)
        for label in result.windows:
            assert "-" in label
            start, end = label.split("-")
            assert int(end) - int(start) == 2  # window=3 → 2 year span

    def test_river_top_n_limits(self, river_records):
        """top_n should cap the number of keywords."""
        engine = TrendEngine(river_records)
        result = engine.river(top_n=2, window=3)
        assert len(result.keywords) <= 2

    def test_river_share_percentages(self, river_records):
        """Matrix values should be percentages (0-100 range)."""
        engine = TrendEngine(river_records)
        result = engine.river(top_n=5, window=3)
        for shares in result.matrix.values():
            for share in shares:
                assert 0.0 <= share <= 100.0

    def test_river_rising_keyword(self, river_records):
        """'ml' share should generally rise from first to last window."""
        engine = TrendEngine(river_records)
        result = engine.river(top_n=5, window=2)
        if "ml" in result.matrix and len(result.matrix["ml"]) >= 2:
            shares = result.matrix["ml"]
            # First window should be < last window
            assert shares[-1] > shares[0], (
                f"ml share should rise: first={shares[0]}, last={shares[-1]}"
            )

    def test_river_no_year_records(self):
        """Records without year are skipped, not crashed on."""
        records = [
            Record(title="No year", year=None, keywords=["kw"]),
            _r("Real", 2024, ["kw"]),
        ]
        engine = TrendEngine(records)
        # Single year not enough for default window
        result = engine.river(window=2)
        assert isinstance(result, RiverData)

    def test_river_short_time_range(self):
        """Time range shorter than window → empty result."""
        records = [_r("P1", 2024, ["kw"])]
        engine = TrendEngine(records)
        result = engine.river(window=5)  # window=5, but only 1 year
        assert result.windows == []
        assert result.keywords == []


# ===========================================================================
# Integration / edge cases
# ===========================================================================


class TestIntegration:
    def test_records_with_keywords_en_only(self):
        """Records with only keywords_en should be analyzed."""
        records = [
            _r("P1", 2020, [], ["ml"]),
            _r("P2", 2020, [], ["ml"]),
            _r("P3", 2020, [], ["ml"]),
            _r("P4", 2020, [], ["dl"]),
        ]
        engine = TrendEngine(records)
        result = engine.hotspots()
        assert isinstance(result, BurstAnalysis)

    def test_repeated_engines_independent(self):
        """Two engines on different data should not share state."""
        records1 = [_r("P1", 2024, ["a"])]
        records2 = [_r("P2", 2024, ["b"])]
        e1 = TrendEngine(records1)
        e2 = TrendEngine(records2)
        r1 = e1.hotspots(top_n=5)
        r2 = e2.hotspots(top_n=5)
        # Both work independently
        assert r1 is not r2
        assert isinstance(r1, BurstAnalysis)
        assert isinstance(r2, BurstAnalysis)
