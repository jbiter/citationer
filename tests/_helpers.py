"""Shared test helpers.

Helpers that depend on pytest fixtures or on multiple project modules live here.
`tests._factories` is kept dependency-light so it can be imported anywhere.
"""

from __future__ import annotations

from pathlib import Path

from citationer.models.record import Record
from citationer.utils.database import CitationDatabase
from citationer.utils.serialization import record_to_db_serializable


def seed_cli_db(clean_cwd: Path, records: list[Record]) -> Path:
    """Insert ``records`` into a fresh SQLite cache.db under ``clean_cwd``.

    Returns the path to the created database.  This replaces the dozen
    near-identical ``_setup_*`` helpers scattered through the CLI test files.
    """
    db_dir = clean_cwd / ".citationer"
    db_dir.mkdir(exist_ok=True)
    db = CitationDatabase(db_dir / "cache.db")
    db.initialize()
    for r in records:
        payload = record_to_db_serializable(r)
        db.insert_record(
            record_data=payload["record_data"],
            authors=payload["authors"],
            keywords=payload["keywords"],
            institutions=payload["institutions"],
            funding=payload["funding"],
            references=payload["references"],
        )
    db.close()
    return db_dir / "cache.db"
