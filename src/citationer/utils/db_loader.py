"""Shared utility to load records from the SQLite database into Record objects."""

from __future__ import annotations

import json as _json
from pathlib import Path

from rich.console import Console

from citationer.models.record import Author, DocType, Institution, Record
from citationer.utils.config import get_db_path
from citationer.utils.database import CitationDatabase


def get_records() -> list[Record]:
    """Load records from DB, returning empty list if not available."""
    console = Console()
    db_path = get_db_path()
    if not db_path.exists():
        console.print("[yellow]⚠ 尚未导入数据，请先运行 citationer import[/yellow]")
        return []
    records = load_records_from_db(db_path)
    if not records:
        console.print("[yellow]⚠ 数据库中没有记录[/yellow]")
    return records


def load_records_from_db(db_path: Path) -> list[Record]:
    """Load all records from the SQLite cache database into Record objects."""
    db = CitationDatabase(db_path)
    db.initialize()

    rows = db.get_all_records()
    records: list[Record] = []

    for row in rows:
        author_rows = db.conn.execute(
            "SELECT * FROM record_authors WHERE record_id = ? ORDER BY author_order",
            (row["id"],),
        ).fetchall()

        kw_rows = db.conn.execute(
            "SELECT keyword FROM record_keywords WHERE record_id = ?",
            (row["id"],),
        ).fetchall()

        inst_rows = db.conn.execute(
            "SELECT * FROM record_institutions WHERE record_id = ?",
            (row["id"],),
        ).fetchall()

        raw_data: dict = {}
        try:
            raw_data = _json.loads(row["raw_data"] or "{}")
        except (_json.JSONDecodeError, TypeError):
            pass

        records.append(
            Record(
                id=row["id"],
                title=row["title"] or "",
                title_en=row["title_en"],
                authors=[
                    Author(
                        full_name=a["full_name"],
                        surname=a["surname"],
                        given_name=a["given_name"],
                        order=a["author_order"],
                        is_corresponding=bool(a["is_corresponding"]),
                        affiliation=a["affiliation"],
                        email=a["email"],
                    )
                    for a in author_rows
                ],
                year=row["year"],
                journal=row["journal"],
                volume=row["volume"],
                issue=row["issue"],
                pages=row["pages"],
                doi=row["doi"],
                issn=row["issn"],
                abstract=row["abstract"],
                abstract_en=row["abstract_en"],
                keywords=[k["keyword"] for k in kw_rows],
                doc_type=DocType(row["doc_type"] or "unknown"),
                language=row["language"],
                institutions=[
                    Institution(
                        name=i["name"],
                        country=i["country"],
                        province=i["province"],
                        city=i["city"],
                        inst_type=i["inst_type"],
                    )
                    for i in inst_rows
                ],
                citation_count=row["citation_count"],
                source_database=row["source_database"] or "",
                source_file=row["source_file"] or "",
                raw_data=raw_data,
            )
        )

    db.close()
    return records
