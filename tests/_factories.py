"""Shared test factories.

This module exists so test files can do
    from tests._factories import make_record
without dragging conftest's fixture-discovery machinery into the import
graph.  conftest.py re-exports `make_record` for backward compat.
"""

from __future__ import annotations

from citationer.models.record import Author, DocType, Institution, Record


def make_record(
    title: str = "Sample Paper",
    year: int | None = 2024,
    journal: str | None = "Nature",
    doi: str | None = None,
    authors: list[Author] | None = None,
    keywords: list[str] | None = None,
    keywords_en: list[str] | None = None,
    abstract: str | None = None,
    language: str | None = "en",
    institutions: list[Institution] | None = None,
    funding: list[str] | None = None,
    references: list[str] | None = None,
    citation_count: int | None = None,
    source_database: str = "TestDB",
    source_file: str = "test.txt",
    doc_type: DocType = DocType.UNKNOWN,
) -> Record:
    """Factory for Record objects with sensible defaults.

    Replaces the four duplicated `make_record` helpers that previously
    existed in test_models, test_stats, test_dedup, and test_phase4, plus
    several `_r()` short aliases added later (see code-review finding #4).
    """
    if authors is None:
        authors = [Author(full_name="Smith, John", order=1)]
    if keywords is None:
        keywords = []
    if institutions is None:
        institutions = []
    return Record(
        title=title,
        year=year,
        journal=journal,
        doi=doi,
        authors=authors,
        keywords=keywords,
        keywords_en=keywords_en,
        abstract=abstract,
        language=language,
        institutions=institutions,
        funding=funding,
        references=references,
        citation_count=citation_count,
        source_database=source_database,
        source_file=source_file,
        doc_type=doc_type,
    )
