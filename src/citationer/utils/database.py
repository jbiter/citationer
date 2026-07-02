"""SQLite cache database for citationer.

Stores parsed records, scan results, and LLM call cache.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class CitationDatabase:
    """SQLite-backed cache for bibliographic records and metadata."""

    DB_FILENAME = "cache.db"

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def initialize(self) -> None:
        """Create tables if they don't exist."""
        c = self.conn
        c.executescript("""
            CREATE TABLE IF NOT EXISTS scan_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT NOT NULL,
                source TEXT,
                record_count INTEGER,
                year_min INTEGER,
                year_max INTEGER,
                scanned_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_database TEXT NOT NULL DEFAULT '',
                source_file TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                title_en TEXT,
                year INTEGER,
                journal TEXT,
                volume TEXT,
                issue TEXT,
                pages TEXT,
                doi TEXT,
                issn TEXT,
                abstract TEXT,
                abstract_en TEXT,
                doc_type TEXT DEFAULT 'unknown',
                language TEXT,
                citation_count INTEGER,
                imported_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT,
                raw_data TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS record_authors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                surname TEXT,
                given_name TEXT,
                author_order INTEGER NOT NULL DEFAULT 1,
                is_corresponding INTEGER DEFAULT 0,
                affiliation TEXT,
                email TEXT,
                FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS record_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                lang TEXT DEFAULT 'zh',
                FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS record_institutions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                country TEXT,
                province TEXT,
                city TEXT,
                inst_type TEXT,
                FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS llm_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE NOT NULL,
                response TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                model TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_records_doi ON records(doi) WHERE doi IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_records_year ON records(year);
            CREATE INDEX IF NOT EXISTS idx_records_source
            ON records(source_database);

            CREATE INDEX IF NOT EXISTS idx_record_authors_record
            ON record_authors(record_id);

            CREATE INDEX IF NOT EXISTS idx_record_keywords_record
            ON record_keywords(record_id);

            CREATE INDEX IF NOT EXISTS idx_record_institutions_record
            ON record_institutions(record_id);
        """)
        self.conn.commit()

    def clear_records(self) -> None:
        """Delete all parsed records."""
        c = self.conn
        c.execute("DELETE FROM record_institutions")
        c.execute("DELETE FROM record_keywords")
        c.execute("DELETE FROM record_authors")
        c.execute("DELETE FROM records")
        self.conn.commit()

    def insert_record(
        self,
        record_data: dict[str, Any],
        authors: list[dict],
        keywords: list[dict],
        institutions: list[dict],
    ) -> int:
        """Insert a single record with related data. Returns the new record ID."""
        c = self.conn
        record_data["imported_at"] = datetime.now(timezone.utc).isoformat()
        record_data.setdefault("raw_data", "{}")
        if isinstance(record_data.get("raw_data"), dict):
            record_data["raw_data"] = json.dumps(record_data["raw_data"], ensure_ascii=False)

        columns = [
            "source_database", "source_file", "title", "title_en", "year",
            "journal", "volume", "issue", "pages", "doi", "issn",
            "abstract", "abstract_en", "doc_type", "language",
            "citation_count", "imported_at", "raw_data",
        ]
        values = [record_data.get(col, "") for col in columns]

        placeholders = ", ".join("?" * len(columns))
        col_names = ", ".join(columns)

        cursor = c.execute(
            f"INSERT INTO records ({col_names}) VALUES ({placeholders})",
            values,
        )
        record_id = cursor.lastrowid

        if record_id:
            for author in authors:
                c.execute(
                    """INSERT INTO record_authors
                       (record_id, full_name, surname, given_name, author_order,
                        is_corresponding, affiliation, email)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        record_id,
                        author.get("full_name", ""),
                        author.get("surname"),
                        author.get("given_name"),
                        author.get("order", 1),
                        1 if author.get("is_corresponding") else 0,
                        author.get("affiliation"),
                        author.get("email"),
                    ),
                )
            for kw in keywords:
                c.execute(
                    "INSERT INTO record_keywords (record_id, keyword, lang) VALUES (?, ?, ?)",
                    (record_id, kw.get("keyword", ""), kw.get("lang", "zh")),
                )
            for inst in institutions:
                c.execute(
                    """INSERT INTO record_institutions
                       (record_id, name, country, province, city, inst_type)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        record_id,
                        inst.get("name", ""),
                        inst.get("country"),
                        inst.get("province"),
                        inst.get("city"),
                        inst.get("inst_type"),
                    ),
                )
            self.conn.commit()

        return record_id

    def insert_scan_log(
        self,
        filepath: str,
        source: str | None,
        record_count: int,
        year_min: int | None,
        year_max: int | None,
    ) -> None:
        """Log a scan result."""
        self.conn.execute(
            """INSERT INTO scan_log (filepath, source, record_count, year_min, year_max)
               VALUES (?, ?, ?, ?, ?)""",
            (filepath, source, record_count, year_min, year_max),
        )
        self.conn.commit()

    def get_all_records(self) -> list[sqlite3.Row]:
        """Get all records from the database."""
        return list(self.conn.execute("SELECT * FROM records ORDER BY year DESC").fetchall())

    def get_record_count(self) -> int:
        """Count total records in the database."""
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM records").fetchone()
        return row["cnt"] if row else 0

    def get_source_stats(self) -> list[sqlite3.Row]:
        """Get record count per source database."""
        return list(self.conn.execute(
            "SELECT source_database, COUNT(*) as cnt "
            "FROM records GROUP BY source_database ORDER BY cnt DESC"
        ).fetchall())

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
