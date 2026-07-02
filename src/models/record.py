"""Unified bibliographic record model."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocType(str, Enum):
    """Type of bibliographic record."""

    ARTICLE = "article"
    REVIEW = "review"
    CONFERENCE = "conference"
    THESIS = "thesis"
    BOOK = "book"
    BOOK_CHAPTER = "book_chapter"
    PATENT = "patent"
    OTHER = "other"
    UNKNOWN = "unknown"


class Author(BaseModel):
    """Author representation with normalized name handling."""

    full_name: str
    surname: str | None = None
    given_name: str | None = None
    order: int = 1  # 1-based author order
    is_corresponding: bool = False
    affiliation: str | None = None
    email: str | None = None

    def __hash__(self) -> int:
        return hash((self.full_name.lower(), self.order))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Author):
            return NotImplemented
        return self.full_name.lower() == other.full_name.lower()


class Institution(BaseModel):
    """Institution / affiliation representation."""

    name: str
    name_en: str | None = None
    country: str | None = None
    province: str | None = None
    city: str | None = None
    inst_type: str | None = None  # university, research_institute, hospital, enterprise


class Record(BaseModel):
    """Unified bibliographic record.

    This is the canonical data model that all parsers produce,
    and all analysis engines consume.
    """

    # --- Core identity ---
    title: str = ""
    title_en: str | None = None

    # --- Authors ---
    authors: list[Author] = []

    # --- Publication info ---
    year: int | None = None
    journal: str | None = None
    journal_en: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None
    doi: str | None = None
    issn: str | None = None

    # --- Content ---
    abstract: str | None = None
    abstract_en: str | None = None
    keywords: list[str] = []
    keywords_en: list[str] | None = None

    # --- Classification ---
    doc_type: DocType = DocType.UNKNOWN
    language: str | None = None  # zh, en, ...

    # --- Institutions ---
    institutions: list[Institution] = []

    # --- Funding ---
    funding: list[str] | None = None

    # --- Citation data ---
    citation_count: int | None = None
    references: list[str] | None = None

    # --- Source tracking ---
    source_database: str = ""  # CNKI, WoS, Scopus, ...
    source_file: str = ""  # original filename
    raw_data: dict[str, Any] = Field(default_factory=dict, exclude=True)

    # --- Internal ---
    id: int | None = None  # DB primary key
    imported_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def first_author(self) -> Author | None:
        """Get the first author."""
        for a in self.authors:
            if a.order == 1:
                return a
        return self.authors[0] if self.authors else None

    @property
    def author_count(self) -> int:
        """Total number of authors."""
        return len(self.authors)

    @property
    def is_solo(self) -> bool:
        """Whether this is a single-author work."""
        return len(self.authors) == 1

    @property
    def keyword_set(self) -> set[str]:
        """All keywords as a normalized set (lowercase, stripped)."""
        kw = {k.strip().lower() for k in self.keywords if k.strip()}
        if self.keywords_en:
            kw.update(k.strip().lower() for k in self.keywords_en if k.strip())
        return kw
