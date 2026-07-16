"""Regression tests for BUG-006: dedup r.year=None wrongly bucketed as year=0."""

from __future__ import annotations

from citationer.analysis.dedup import DedupEngine
from citationer.models.record import Author, Record


def _r(title: str, year: int | None = None) -> Record:
    return Record(
        title=title,
        year=year,
        authors=[Author(full_name="Smith, J.", order=1)],
        keywords=["shared_kw"],
        source_database="TestDB",
    )


class TestBug006Regression:
    """BUG-006: year=None records must NOT be merged just because titles match."""

    def test_two_year_none_with_similar_titles_not_merged(self):
        """Two records with year=None and very similar titles should NOT merge.

        Pre-fix behavior: bucketized as year=0 → high title similarity
        triggers Layer 2 merge.
        Post-fix behavior: year=None records are skipped in bucketing.
        """
        r1 = _r("深度学习方法研究", year=None)
        r2 = _r("深度学习方法研究（续）", year=None)
        engine = DedupEngine()
        merged, log = engine.deduplicate([r1, r2])
        assert len(merged) == 2, (
            f"year=None records should not be merged, got {len(merged)}"
        )
        assert log == []

    def test_year_none_records_with_identical_titles_not_merged(self):
        """Even identical titles + year=None should not merge.

        (No DOI match → no Layer 1. No year → no Layer 2/3 bucket.)
        """
        r1 = _r("Same Title", year=None, )
        r2 = _r("Same Title", year=None, )
        engine = DedupEngine()
        merged, log = engine.deduplicate([r1, r2])
        assert len(merged) == 2
        assert log == []

    def test_year_none_mixed_with_year_present(self):
        """year=None records and year=2024 records with same title → 2 records.

        Pre-fix: year=None bucket (0) vs year=2024 bucket separate;
        no merge between them.  But if year=None records cluster together
        they wrongly merge.  Verify the latter doesn't happen.
        """
        r1 = _r("Duplicate Title X", year=None)
        r2 = _r("Duplicate Title X", year=None)
        r3 = _r("Duplicate Title X", year=2024)
        r4 = _r("Unique Title Y", year=2024)
        engine = DedupEngine()
        merged, log = engine.deduplicate([r1, r2, r3, r4])
        # r1+r2 must NOT merge (year=None)
        # r3 alone in year=2024 bucket; r4 different title
        # Expected: 4 records
        assert len(merged) == 4

    def test_layer2_with_year_still_works(self):
        """Regression check: legitimate year-based merges still happen."""
        r1 = _r("Machine Learning in Healthcare", year=2024)
        r2 = _r("Machine Learning in Healthcare Study", year=2024)
        engine = DedupEngine()
        merged, log = engine.deduplicate([r1, r2])
        # Same year, similar titles → should merge
        assert len(merged) == 1
        assert any(entry["layer"] == 2 for entry in log)

    def test_layer3_first_author_with_year_still_works(self):
        """Layer 2/3 still merges legitimate same-year + same-author records.

        Note: with title 100% identical, Layer 2 (title fuzzy high) fires
        first.  We verify the merge happened via any layer 2 or 3 entry.
        """
        r1 = _r("ML Research Overview", year=2023,
                )  # first_author=Smith, J.
        r2 = _r("ML Research Overview", year=2023,
                )  # same author, same year
        engine = DedupEngine()
        merged, log = engine.deduplicate([r1, r2])
        assert len(merged) == 1
        assert any(entry["layer"] in (2, 3) for entry in log)

    def test_year_none_records_dont_collide_with_year_zero(self):
        """year=None records must NOT collide with year=0 records.

        Pre-fix: both go to year=0 bucket, possibly causing false merge.
        """
        r1 = _r("Study Alpha", year=None)
        r2 = _r("Study Alpha", year=0)  # rare but valid
        engine = DedupEngine()
        merged, log = engine.deduplicate([r1, r2])
        assert len(merged) == 2  # Should not merge
        assert log == []
