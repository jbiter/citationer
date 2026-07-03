"""Tests for the statistics engine."""

import pytest

from citationer.analysis.stats import StatsEngine
from citationer.models.record import Author, Institution, Record


def make_record(title: str, year: int, journal: str = "", authors=None, citations=0, **kwargs):
    """Helper to create test records quickly."""
    return Record(
        title=title,
        year=year,
        journal=journal,
        authors=authors or [],
        citation_count=citations,
        **kwargs,
    )


class TestOverviewStats:
    def test_empty_records(self):
        engine = StatsEngine([])
        stats = engine.overview()
        assert stats.total_records == 0
        assert stats.year_min is None

    def test_basic_overview(self):
        records = [
            make_record("Paper A", 2024, "Journal X", [
                Author(full_name="Author 1"),
                Author(full_name="Author 2"),
            ], citations=10),
            make_record("Paper B", 2023, "Journal X", [
                Author(full_name="Author 1"),
                Author(full_name="Author 2"),
            ], citations=5),
            make_record("Paper C", 2022, "Journal X", [
                Author(full_name="Author 3"),
                Author(full_name="Author 4"),
                Author(full_name="Author 5"),
            ], citations=2),
        ]

        engine = StatsEngine(records)
        stats = engine.overview()

        assert stats.total_records == 3
        assert stats.year_min == 2022
        assert stats.year_max == 2024
        assert stats.num_journals == 1
        assert stats.num_authors == 5  # unique authors
        assert stats.solo_rate == 0.0  # all papers have > 1 author
        assert stats.coop_rate == 1.0
        assert stats.avg_citations == pytest.approx(17 / 3)

    def test_h_index(self):
        records = [
            make_record(f"Paper {i}", 2020 + i, citations=c)
            for i, c in enumerate([10, 8, 5, 3, 1])
        ]
        engine = StatsEngine(records)
        stats = engine.overview()
        # Citations sorted: 10, 8, 5, 3, 1
        # h-index = 3 (3 papers with >= 3 citations)
        assert stats.h_index == 3

    def test_solo_rate(self):
        records = [
            make_record("Solo", 2024, authors=[Author(full_name="A")]),
            make_record("Solo 2", 2024, authors=[Author(full_name="B")]),
            make_record("Coop", 2024, authors=[
                Author(full_name="C"),
                Author(full_name="D"),
            ]),
        ]
        engine = StatsEngine(records)
        stats = engine.overview()
        assert stats.solo_rate == pytest.approx(2 / 3)
        assert stats.coop_rate == pytest.approx(1 / 3)


class TestYearlyStats:
    def test_yearly_counts(self):
        records = [
            make_record("A", 2024),
            make_record("B", 2024),
            make_record("C", 2023),
            make_record("D", 2022),
        ]
        engine = StatsEngine(records)
        stats = engine.yearly()

        assert stats.year_counts == {2022: 1, 2023: 1, 2024: 2}
        assert stats.cumulative == {2022: 1, 2023: 2, 2024: 4}

    def test_yearly_empty(self):
        engine = StatsEngine([])
        stats = engine.yearly()
        assert stats.year_counts == {}


class TestJournalStats:
    def test_top_journals(self):
        records = [
            make_record("A", 2024, "Nature"),
            make_record("B", 2024, "Nature"),
            make_record("C", 2024, "Science"),
            make_record("D", 2024, "Nature"),
            make_record("E", 2024, "Cell"),
        ]
        engine = StatsEngine(records)
        result = engine.journals(top_n=2)
        assert len(result.items) == 2
        assert result.items[0][0] == "Nature"
        assert result.items[0][1] == 3
        assert result.total_unique == 3


class TestAuthorStats:
    def test_top_authors(self):
        records = [
            make_record("A", 2024, authors=[
                Author(full_name="Smith, J", order=1),
            ], citations=5),
            make_record("B", 2024, authors=[
                Author(full_name="Smith, J", order=1),
            ], citations=3),
            make_record("C", 2024, authors=[
                Author(full_name="Jones, M", order=1),
            ], citations=10),
        ]
        engine = StatsEngine(records)
        result = engine.authors(top_n=2)
        assert len(result.top_authors.items) == 2
        # Smith has 2 papers
        assert result.top_authors.items[0][1] == 2

    def test_author_h_index_computation(self):
        """Verify author H-index from citation counts."""
        records = [
            make_record("A", 2024, authors=[
                Author(full_name="Smith, J", order=1),
            ], citations=10),
            make_record("B", 2024, authors=[
                Author(full_name="Smith, J", order=1),
            ], citations=5),
            make_record("C", 2024, authors=[
                Author(full_name="Smith, J", order=1),
            ], citations=3),
        ]
        engine = StatsEngine(records)
        result = engine.authors(top_n=1)
        # Smith's citations: [10, 5, 3] → h-index = 3
        h_dict = dict(result.author_h_index)
        assert h_dict.get("Smith, J", 0) == 3


class TestYearlyBySource:
    def test_yearly_by_source(self):
        records = [
            make_record("A", 2024, source_database="WoS"),
            make_record("B", 2024, source_database="WoS"),
            make_record("C", 2023, source_database="CNKI"),
        ]
        engine = StatsEngine(records)
        result = engine.yearly_by_source()
        assert "WoS" in result
        assert "CNKI" in result
        assert result["WoS"][2024] == 2
        assert result["CNKI"][2023] == 1

    def test_yearly_by_source_empty(self):
        engine = StatsEngine([])
        result = engine.yearly_by_source()
        assert result == {}


class TestInstitutionsEdgeCases:
    def test_institutions_empty(self):
        engine = StatsEngine([])
        result = engine.institutions(top_n=10)
        assert result.total_unique == 0
        assert result.items == []

    def test_institutions_with_country(self):
        records = [
            make_record("A", 2024, institutions=[
                Institution(name="Harvard", country="USA"),
                Institution(name="MIT", country="USA"),
                Institution(name="Tsinghua", country="China"),
            ]),
        ]
        engine = StatsEngine(records)
        stats = engine.overview()
        assert stats.num_institutions == 3
        assert stats.num_countries == 2
