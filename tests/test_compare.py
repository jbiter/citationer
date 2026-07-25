"""Tests for the multi-dataset comparison engine."""

from __future__ import annotations

import pytest

from citationer.analysis.compare import CompareEngine, _group_records
from citationer.models.record import Author, Institution, Record


def _make_record(
    title: str,
    year: int | None,
    source_database: str,
    source_file: str = "test.txt",
    **kwargs,
) -> Record:
    return Record(
        title=title,
        year=year,
        source_database=source_database,
        source_file=source_file,
        **kwargs,
    )


class TestGroupRecords:
    def test_by_database(self):
        records = [
            _make_record("A", 2024, "DB1"),
            _make_record("B", 2023, "DB2"),
            _make_record("C", 2022, "DB1+DB2"),
        ]
        groups = _group_records(records, by="database")
        assert set(groups) == {"DB1", "DB2"}
        assert len(groups["DB1"]) == 2
        assert len(groups["DB2"]) == 2

    def test_by_file(self):
        records = [
            _make_record("A", 2024, "DB1", "a.txt"),
            _make_record("B", 2023, "DB2", "b.txt"),
        ]
        groups = _group_records(records, by="file")
        assert set(groups) == {"a.txt", "b.txt"}

    def test_empty_key_skipped(self):
        records = [
            _make_record("A", 2024, ""),
            _make_record("B", 2023, "DB1"),
        ]
        groups = _group_records(records, by="database")
        assert set(groups) == {"DB1"}


class TestCompareOverview:
    def test_overview_counts(self):
        records = [
            _make_record(
                "A",
                2024,
                "DB1",
                journal="Nature",
                authors=[Author(full_name="Alice", order=1)],
                keywords=["ml"],
            ),
            _make_record(
                "B",
                2023,
                "DB2",
                journal="Science",
                authors=[Author(full_name="Bob", order=1)],
                keywords=["ai"],
            ),
        ]
        engine = CompareEngine(records)
        overviews, overlaps = engine.overview(top_n=5)
        assert overviews["DB1"].total_records == 1
        assert overviews["DB2"].total_records == 1
        assert len(overlaps) == 1
        assert overlaps[0].dataset_a == "DB1"
        assert overlaps[0].dataset_b == "DB2"

    def test_doi_overlap(self):
        records = [
            _make_record("A", 2024, "DB1", doi="10.1/a"),
            _make_record("B", 2024, "DB2", doi="10.1/a"),
            _make_record("C", 2023, "DB2", doi="10.1/c"),
        ]
        engine = CompareEngine(records)
        _, overlaps = engine.overview()
        assert overlaps[0].doi_overlap == 1

    def test_fuzzy_title_overlap(self):
        records = [
            _make_record("Machine Learning in Healthcare", 2024, "DB1"),
            _make_record("Machine Learning in Healthcare (Review)", 2024, "DB2"),
        ]
        engine = CompareEngine(records)
        _, overlaps = engine.overview(threshold=0.7)
        assert overlaps[0].title_overlap == 1

    def test_keyword_jaccard(self):
        records = [
            _make_record("A", 2024, "DB1", keywords=["ml", "health"]),
            _make_record("B", 2024, "DB2", keywords=["ml", "ai"]),
        ]
        engine = CompareEngine(records)
        _, overlaps = engine.overview()
        assert overlaps[0].keyword_jaccard == pytest.approx(1 / 3)

    def test_shared_authors_and_institutions(self):
        records = [
            _make_record(
                "A",
                2024,
                "DB1",
                authors=[Author(full_name="Alice", order=1)],
                institutions=[Institution(name="MIT")],
            ),
            _make_record(
                "B",
                2023,
                "DB2",
                authors=[Author(full_name="Alice", order=1)],
                institutions=[Institution(name="MIT")],
            ),
        ]
        engine = CompareEngine(records)
        _, overlaps = engine.overview()
        assert overlaps[0].shared_authors == [("Alice", 1)]
        assert overlaps[0].shared_institutions == [("MIT", 1)]


class TestCompareTrends:
    def test_trends(self):
        records = [
            _make_record("A", 2024, "DB1"),
            _make_record("B", 2024, "DB1"),
            _make_record("C", 2023, "DB2"),
        ]
        engine = CompareEngine(records)
        result = engine.trends()
        assert result.year_counts["DB1"][2024] == 2
        assert result.year_counts["DB2"][2023] == 1
        assert result.year_min == 2023
        assert result.year_max == 2024


class TestCompareTopics:
    def test_topics(self):
        records = [
            _make_record("A", 2024, "DB1", keywords=["ml", "health"]),
            _make_record("B", 2024, "DB2", keywords=["ml", "ai"]),
        ]
        engine = CompareEngine(records)
        result = engine.topics(top_n=5)
        assert "ml" in [k for k, _ in result.dataset_keywords["DB1"]]
        assert result.pairwise_jaccard[("DB1", "DB2")] == 1 / 3
        assert "ml" in result.shared_keywords[("DB1", "DB2")]


class TestCompareNetwork:
    def test_shared_authors(self):
        records = [
            _make_record(
                "A", 2024, "DB1", authors=[Author(full_name="Alice", order=1)]
            ),
            _make_record(
                "B", 2023, "DB2", authors=[Author(full_name="Alice", order=1)]
            ),
        ]
        engine = CompareEngine(records)
        result = engine.network(collab_type="authors")
        assert "Alice" in [n for n, _ in result.shared_nodes["DB1"]]
        assert result.dataset_node_counts["DB1"] == 1

    def test_shared_institutions(self):
        records = [
            _make_record(
                "A",
                2024,
                "DB1",
                authors=[Author(full_name="Alice", order=1)],
                institutions=[Institution(name="MIT")],
            ),
            _make_record(
                "B",
                2023,
                "DB2",
                authors=[Author(full_name="Bob", order=1)],
                institutions=[Institution(name="MIT")],
            ),
        ]
        engine = CompareEngine(records)
        result = engine.network(collab_type="institutions")
        assert "MIT" in [n for n, _ in result.shared_nodes["DB1"]]

    def test_cross_edges(self):
        records = [
            _make_record(
                "A",
                2024,
                "DB1",
                authors=[
                    Author(full_name="Alice", order=1),
                    Author(full_name="Bob", order=2),
                ],
            ),
            _make_record(
                "B",
                2024,
                "DB2",
                authors=[
                    Author(full_name="Alice", order=1),
                    Author(full_name="Carol", order=2),
                ],
            ),
        ]
        engine = CompareEngine(records)
        result = engine.network(collab_type="authors", min_papers=1)
        pairs = {(tuple(sorted([a, b])), w) for a, b, w in result.cross_edges}
        assert any("Alice" in pair[0] and "Bob" in pair[0] for pair in pairs)


class TestCompareEngineLessThanTwoDatasets:
    def test_single_dataset_returns_warning(self, capsys):
        records = [_make_record("A", 2024, "DB1")]
        engine = CompareEngine(records)
        assert engine.dataset_names == ["DB1"]
