"""Tests for the unified data model."""

from citationer.models.record import Author, DocType, Record


class TestAuthor:
    def test_create_author(self):
        author = Author(full_name="Zhang, Wei", order=1)
        assert author.full_name == "Zhang, Wei"
        assert author.order == 1
        assert not author.is_corresponding

    def test_author_equality(self):
        a1 = Author(full_name="Zhang, Wei", order=1)
        a2 = Author(full_name="ZHANG, WEI", order=2)
        assert a1 == a2

    def test_author_hash(self):
        a1 = Author(full_name="Zhang, Wei")
        a2 = Author(full_name="zhang, wei")
        assert hash(a1) == hash(a2)


class TestRecord:
    def test_create_minimal_record(self):
        r = Record(title="Test Paper")
        assert r.title == "Test Paper"
        assert r.doc_type == DocType.UNKNOWN
        assert r.authors == []
        assert r.keywords == []

    def test_first_author(self):
        r = Record(
            title="Test",
            authors=[
                Author(full_name="First Author", order=1),
                Author(full_name="Second Author", order=2),
            ],
        )
        assert r.first_author is not None
        assert r.first_author.full_name == "First Author"

    def test_first_author_empty(self):
        r = Record(title="Test")
        assert r.first_author is None

    def test_is_solo(self):
        solo = Record(
            title="Solo Paper",
            authors=[Author(full_name="Only Author")],
        )
        assert solo.is_solo

        coop = Record(
            title="Coop Paper",
            authors=[
                Author(full_name="A", order=1),
                Author(full_name="B", order=2),
            ],
        )
        assert not coop.is_solo

    def test_author_count(self):
        r = Record(
            title="Test",
            authors=[
                Author(full_name="A"),
                Author(full_name="B"),
                Author(full_name="C"),
            ],
        )
        assert r.author_count == 3

    def test_keyword_set(self):
        r = Record(
            title="Test",
            keywords=["Machine Learning", "Deep Learning"],
            keywords_en=["AI", "Neural Networks"],
        )
        kw_set = r.keyword_set
        assert "machine learning" in kw_set
        assert "deep learning" in kw_set
        assert "ai" in kw_set
        assert "neural networks" in kw_set
