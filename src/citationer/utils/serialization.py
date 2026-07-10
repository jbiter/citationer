"""Shared utility for converting Record objects to DB-insertable data."""

from __future__ import annotations

from citationer.models.record import Record


def record_to_db_serializable(record: Record) -> dict:
    """Convert a Record into DB-insertable dicts.

    Returns a dict with keys: record_data, authors, keywords, institutions.
    Each value is the format expected by CitationDatabase.insert_record().
    """
    authors_data = [
        {
            "full_name": a.full_name,
            "surname": a.surname,
            "given_name": a.given_name,
            "order": a.order,
            "is_corresponding": a.is_corresponding,
            "affiliation": a.affiliation,
            "email": a.email,
        }
        for a in record.authors
    ]

    # Tag both lists with field-specific markers so the loader can
    # distinguish them regardless of record.language (BUG-003 fix).
    keywords_data = [
        {"keyword": k, "lang": "__keywords__"} for k in record.keywords
    ]
    if record.keywords_en:
        keywords_data.extend(
            {"keyword": k, "lang": "__keywords_en__"} for k in record.keywords_en
        )

    institutions_data = [
        {
            "name": i.name,
            "name_en": i.name_en,
            "country": i.country,
            "province": i.province,
            "city": i.city,
            "inst_type": i.inst_type,
        }
        for i in record.institutions
    ]

    record_data = {
        "source_database": record.source_database,
        "source_file": record.source_file,
        "title": record.title,
        "title_en": record.title_en,
        "year": record.year,
        "journal": record.journal,
        "volume": record.volume,
        "issue": record.issue,
        "pages": record.pages,
        "doi": record.doi,
        "issn": record.issn,
        "abstract": record.abstract,
        "abstract_en": record.abstract_en,
        "doc_type": record.doc_type.value,
        "language": record.language,
        "citation_count": record.citation_count,
        "raw_data": record.raw_data,
    }

    return {
        "record_data": record_data,
        "authors": authors_data,
        "keywords": keywords_data,
        "institutions": institutions_data,
        "funding": record.funding,
        "references": record.references,
    }
