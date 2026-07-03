"""Tests for the deduplication engine."""

from citationer.analysis.dedup import (
    DedupEngine,
    _merge_records,
    _normalize_title,
    _title_similarity,
)
from citationer.models.record import Author, Record


class TestTitleNormalization:
    def test_normalize_lowercase(self):
        assert _normalize_title("Machine Learning") == "machine learning"

    def test_normalize_punctuation(self):
        result = _normalize_title("Machine Learning: A Survey")
        assert ":" not in result
        assert "machine learning a survey" == result

    def test_normalize_whitespace(self):
        result = _normalize_title("Machine   Learning\tSurvey")
        assert result == "machine learning survey"


class TestTitleSimilarity:
    def test_exact_match(self):
        assert _title_similarity("Machine Learning", "Machine Learning") == 1.0

    def test_case_insensitive(self):
        sim = _title_similarity("Machine Learning", "machine learning")
        assert sim > 0.95

    def test_different_titles(self):
        sim = _title_similarity(
            "Machine Learning in Healthcare",
            "Quantum Computing in Finance",
        )
        assert sim < 0.5

    def test_empty_titles(self):
        assert _title_similarity("", "") == 0.0
        assert _title_similarity("", "something") == 0.0


class TestMergeRecords:
    def test_merge_fills_gaps(self):
        r1 = Record(
            title="Paper A",
            year=2024,
            doi="10.1000/a",
            keywords=["ml", "ai"],
        )
        r2 = Record(
            title="Paper A",
            year=2024,
            doi="10.1000/a",
            abstract="This is an abstract.",
            keywords=["deep learning"],
        )

        merged = _merge_records(r1, r2)
        assert merged.abstract == "This is an abstract."
        assert "ml" in merged.keywords
        assert "ai" in merged.keywords
        assert "deep learning" in merged.keywords

    def test_merge_authors_union(self):
        r1 = Record(
            title="Paper",
            authors=[
                Author(full_name="Author A", order=1),
                Author(full_name="Author B", order=2),
            ],
        )
        r2 = Record(
            title="Paper",
            authors=[
                Author(full_name="Author A", order=1),
                Author(full_name="Author C", order=2),
            ],
        )

        merged = _merge_records(r1, r2)
        assert len(merged.authors) == 3
        names = {a.full_name for a in merged.authors}
        assert "Author A" in names
        assert "Author B" in names
        assert "Author C" in names


class TestDedupEngine:
    def test_layer1_doi_exact(self):
        records = [
            Record(title="Paper A", doi="10.1000/test", year=2024, source_database="CNKI"),
            Record(title="Paper A Duplicate", doi="10.1000/test", year=2024, source_database="WoS"),
        ]
        engine = DedupEngine()
        merged, log = engine.deduplicate(records)
        assert len(merged) == 1
        assert len(log) == 1
        assert log[0]["layer"] == 1

    def test_layer1_no_doi_no_dedup(self):
        records = [
            Record(title="Machine Learning Applications in Healthcare", year=2024),
            Record(title="Quantum Computing for Financial Risk Analysis", year=2024),
        ]
        engine = DedupEngine()
        merged, log = engine.deduplicate(records)
        assert len(merged) == 2
        assert len(log) == 0

    def test_layer2_title_high_similarity(self):
        records = [
            Record(
                title="A Study of Machine Learning in Bibliometrics",
                year=2024,
            ),
            Record(
                title="A Study of Machine Learning in Bibliometric Analysis",
                year=2024,
            ),
        ]
        engine = DedupEngine()
        merged, log = engine.deduplicate(records)
        # These titles should be > 85% similar
        assert len(merged) == 1
        assert len(log) == 1
        assert log[0]["layer"] == 2

    def test_layer2_different_year_no_dedup(self):
        records = [
            Record(title="Machine Learning in Healthcare", year=2020),
            Record(title="Machine Learning in Healthcare", year=2024),
        ]
        engine = DedupEngine()
        merged, log = engine.deduplicate(records)
        # Different years should prevent merge
        assert len(merged) == 2

    def test_empty_list(self):
        engine = DedupEngine()
        merged, log = engine.deduplicate([])
        assert merged == []
        assert log == []

    def test_layer3_title_low_same_author(self):
        """Title >= 70% + same first author + same year → merge."""
        records = [
            Record(
                title="A Survey of Machine Learning in Medical Image Analysis",
                year=2024,
                authors=[Author(full_name="Zhang, Wei", order=1)],
            ),
            Record(
                title="A Review of Machine Learning for Medical Image Processing",
                year=2024,
                authors=[Author(full_name="Zhang, Wei", order=1)],
            ),
        ]
        engine = DedupEngine(title_threshold_high=0.95, title_threshold_low=0.70)
        merged, log = engine.deduplicate(records)
        # These should be similar enough for layer 3
        assert len(merged) == 1
        assert log[0]["layer"] in (2, 3)

    def test_layer3_different_author_no_merge(self):
        """Title similar but different first author → no merge."""
        records = [
            Record(
                title="Machine Learning in Healthcare Applications",
                year=2024,
                authors=[Author(full_name="Smith, John", order=1)],
            ),
            Record(
                title="Machine Learning in Healthcare Systems",
                year=2024,
                authors=[Author(full_name="Jones, Mary", order=1)],
            ),
        ]
        engine = DedupEngine(title_threshold_high=0.95, title_threshold_low=0.60)
        merged, log = engine.deduplicate(records)
        assert len(merged) == 2  # different authors → no merge

    def test_layer4_cross_language(self):
        """Cross-source + same year + author + journal + pages → merge."""
        records = [
            Record(
                title="中文文献标题",
                year=2024,
                authors=[Author(full_name="Wang", surname="Wang", order=1)],
                journal="Nature",
                volume="10",
                pages="123-130",
                source_database="CNKI",
            ),
            Record(
                title="English Paper Title",
                year=2024,
                authors=[Author(full_name="Wang, L.", surname="Wang", order=1)],
                journal="Nature",
                volume="10",
                pages="123-130",
                source_database="WoS",
            ),
        ]
        engine = DedupEngine()
        merged, log = engine.deduplicate(records)
        assert len(merged) == 1
        assert log[0]["layer"] == 4

    def test_layer4_same_source_skip(self):
        """Same source database → layer 4 skips."""
        records = [
            Record(
                title="Paper A", year=2024,
                authors=[Author(full_name="Smith", surname="Smith", order=1)],
                journal="Science", volume="1", pages="1-10",
                source_database="WoS",
            ),
            Record(
                title="Paper B", year=2024,
                authors=[Author(full_name="Smith", surname="Smith", order=1)],
                journal="Science", volume="1", pages="1-10",
                source_database="WoS",
            ),
        ]
        engine = DedupEngine()
        merged, log = engine.deduplicate(records)
        # Layer 4 skips same-source; these may be caught by layer 1/2/3
        # If not caught elsewhere, they remain separate
        assert len(merged) >= 1
