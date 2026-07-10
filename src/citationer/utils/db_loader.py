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
    """Load all records from the SQLite cache into Record objects.

    Uses bulk queries (4 total) instead of per-record queries (3N+1),
    so loading 10000 records is ~1000× faster.
    """
    db = CitationDatabase(db_path)
    db.initialize()

    rows = db.get_all_records()
    if not rows:
        db.close()
        return []

    record_ids = [r["id"] for r in rows]

    # ── Bulk-load authors, keywords, institutions ──────────────
    author_map: dict[int, list] = {rid: [] for rid in record_ids}
    placeholders = ",".join("?" * len(record_ids))
    for arow in db.conn.execute(
        f"SELECT * FROM record_authors WHERE record_id IN ({placeholders}) ORDER BY author_order",
        record_ids,
    ).fetchall():
        author_map[arow["record_id"]].append(
            Author(
                full_name=arow["full_name"],
                surname=arow["surname"],
                given_name=arow["given_name"],
                order=arow["author_order"],
                is_corresponding=bool(arow["is_corresponding"]),
                affiliation=arow["affiliation"],
                email=arow["email"],
            )
        )

    # Funding
    fund_map: dict[int, list[str]] = {rid: [] for rid in record_ids}
    for frow in db.conn.execute(
        f"SELECT record_id, funder FROM record_funding WHERE record_id IN ({placeholders})",
        record_ids,
    ).fetchall():
        fund_map[frow["record_id"]].append(frow["funder"])

    # References
    ref_map: dict[int, list[str]] = {rid: [] for rid in record_ids}
    for rrow in db.conn.execute(
        f"SELECT record_id, ref_text FROM record_references WHERE record_id IN ({placeholders})",
        record_ids,
    ).fetchall():
        ref_map[rrow["record_id"]].append(rrow["ref_text"])

    kw_main_map: dict[int, list[str]] = {rid: [] for rid in record_ids}
    kw_en_explicit: dict[int, list[str]] = {rid: [] for rid in record_ids}
    for krow in db.conn.execute(
        f"SELECT record_id, keyword, lang FROM record_keywords WHERE record_id IN ({placeholders})",
        record_ids,
    ).fetchall():
        lang = krow["lang"] or ""
        if lang == "__keywords__":
            kw_main_map[krow["record_id"]].append(krow["keyword"])
        elif lang == "__keywords_en__":
            kw_en_explicit[krow["record_id"]].append(krow["keyword"])
        # Legacy: lang="en"/"zh" rows are ignored (BUG-003 fix)

    inst_map: dict[int, list] = {rid: [] for rid in record_ids}
    for irow in db.conn.execute(
        f"SELECT * FROM record_institutions WHERE record_id IN ({placeholders})",
        record_ids,
    ).fetchall():
        inst_map[irow["record_id"]].append(
            Institution(
                name=irow["name"],
                country=irow["country"],
                province=irow["province"],
                city=irow["city"],
                inst_type=irow["inst_type"],
            )
        )

    db.close()

    # ── Assemble Record objects ───────────────────────────────
    def _opt_int(value):
        """Convert empty string / None to None; pass through ints."""
        if value is None:
            return None
        if isinstance(value, int):
            return value
        if value == "" or str(value).strip() == "":
            return None
        return value

    records: list[Record] = []
    for row in rows:
        rid = row["id"]
        raw_data: dict = {}
        try:
            raw_data = _json.loads(row["raw_data"] or "{}")
        except (_json.JSONDecodeError, TypeError):
            pass

        # BUG-003 fix: serializer tags record.keywords with "__keywords__"
        # and record.keywords_en with "__keywords_en__" so we can preserve
        # the original split round-trip (independent of record.language).
        primary_kw = kw_main_map.get(rid, [])
        secondary_kw = kw_en_explicit.get(rid, []) or None

        records.append(
            Record(
                id=rid,
                title=row["title"] or "",
                title_en=row["title_en"],
                authors=author_map.get(rid, []),
                year=_opt_int(row["year"]),
                journal=row["journal"],
                volume=row["volume"],
                issue=row["issue"],
                pages=row["pages"],
                doi=row["doi"],
                issn=row["issn"],
                abstract=row["abstract"],
                abstract_en=row["abstract_en"],
                keywords=primary_kw,
                keywords_en=secondary_kw,
                doc_type=DocType(row["doc_type"] or "unknown"),
                language=row["language"],
                institutions=inst_map.get(rid, []),
                citation_count=_opt_int(row["citation_count"]),
                source_database=row["source_database"] or "",
                source_file=row["source_file"] or "",
                raw_data=raw_data,
                funding=fund_map.get(rid) or None,
                references=ref_map.get(rid) or None,
            )
        )

    return records
