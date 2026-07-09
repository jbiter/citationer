"""Tests for SQLite persistence layer (database, db_loader, serialization).

Covers:
- CitationDatabase: init, insert (single + batch), clear, scan log, queries
- LLM cache: get / save / stats
- load_records_from_db: round-trip, empty DB, missing relations
- record_to_db_serializable: Record → DB dict conversion (all field branches)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from citationer.models.record import Author, DocType, Institution, Record
from citationer.utils.database import CitationDatabase
from citationer.utils.db_loader import load_records_from_db
from citationer.utils.serialization import record_to_db_serializable


# ===========================================================================
# CitationDatabase — initialization
# ===========================================================================


class TestDatabaseInit:
    def test_init_creates_db_file(self, tmp_path: Path):
        """Database file should be created on first conn access."""
        db = CitationDatabase(tmp_path / "subdir" / "cache.db")
        # Connection triggers directory creation
        _ = db.conn
        assert (tmp_path / "subdir").exists()
        assert (tmp_path / "subdir" / "cache.db").exists()

    def test_init_idempotent(self, tmp_db: CitationDatabase):
        """Calling initialize() twice should not raise."""
        tmp_db.initialize()
        tmp_db.initialize()  # second call is a no-op
        # Tables still queryable
        assert tmp_db.get_record_count() == 0

    def test_all_expected_tables_exist(self, tmp_db: CitationDatabase):
        """All 7 tables should exist after initialize()."""
        expected = {
            "scan_log",
            "records",
            "record_authors",
            "record_keywords",
            "record_institutions",
            "record_funding",
            "record_references",
            "llm_cache",
        }
        rows = tmp_db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        actual = {r["name"] for r in rows}
        assert expected.issubset(actual), f"Missing tables: {expected - actual}"

    def test_indexes_created(self, tmp_db: CitationDatabase):
        """All 6 indexes should be created after initialize()."""
        rows = tmp_db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
        ).fetchall()
        index_names = {r["name"] for r in rows}
        # Some indexes may be auto-created by SQLite; we expect at least these
        assert "idx_records_doi" in index_names
        assert "idx_records_year" in index_names
        assert "idx_records_source" in index_names
        assert "idx_record_authors_record" in index_names

    def test_wal_mode_enabled(self, tmp_db: CitationDatabase):
        """Database should be in WAL journal mode for concurrent reads."""
        mode = tmp_db.conn.execute("PRAGMA journal_mode").fetchone()
        assert mode[0].lower() == "wal"

    def test_foreign_keys_enabled(self, tmp_db: CitationDatabase):
        """Foreign key constraints should be enforced."""
        fk = tmp_db.conn.execute("PRAGMA foreign_keys").fetchone()
        assert fk[0] == 1


# ===========================================================================
# CitationDatabase — insert_record
# ===========================================================================


class TestInsertRecord:
    def test_insert_minimal(self, tmp_db: CitationDatabase):
        """Insert a record with only required fields."""
        rid = tmp_db.insert_record(
            record_data={
                "title": "Minimal",
                "source_database": "TestDB",
                "source_file": "t.txt",
            },
            authors=[],
            keywords=[],
            institutions=[],
        )
        assert rid is not None
        assert rid > 0
        assert tmp_db.get_record_count() == 1

    def test_insert_full_record(self, sample_records: list[Record]):
        """Insert a record with all fields populated."""
        db = CitationDatabase(None)  # type: ignore[arg-type]
        # Use a temp path
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "t.db"
            db = CitationDatabase(db_path)
            db.initialize()

            r = sample_records[0]  # full record
            payload = record_to_db_serializable(r)
            rid = db.insert_record(
                record_data=payload["record_data"],
                authors=payload["authors"],
                keywords=payload["keywords"],
                institutions=payload["institutions"],
                funding=payload["funding"],
                references=payload["references"],
            )

            assert rid is not None
            # Verify record row
            row = db.conn.execute(
                "SELECT * FROM records WHERE id = ?", (rid,)
            ).fetchone()
            assert row["title"] == r.title
            assert row["year"] == r.year
            assert row["doi"] == r.doi

            # Verify authors (2 authors)
            authors = db.conn.execute(
                "SELECT * FROM record_authors WHERE record_id = ? ORDER BY author_order",
                (rid,),
            ).fetchall()
            assert len(authors) == 2

            # Verify keywords (zh + en)
            kws = db.conn.execute(
                "SELECT * FROM record_keywords WHERE record_id = ?", (rid,)
            ).fetchall()
            assert len(kws) == 4  # 2 zh + 2 en

            # Verify funding (None in this sample)
            funds = db.conn.execute(
                "SELECT * FROM record_funding WHERE record_id = ?", (rid,)
            ).fetchall()
            assert len(funds) == 0

            db.close()

    def test_insert_with_funding_and_references(self, tmp_db: CitationDatabase):
        """Funding and references are stored in dedicated tables."""
        rid = tmp_db.insert_record(
            record_data={
                "title": "Funded Paper",
                "source_database": "WoS",
                "source_file": "f.txt",
            },
            authors=[],
            keywords=[],
            institutions=[],
            funding=["NSF Grant #12345", "NIH R01-67890"],
            references=["Smith 2020", "Jones 2021", "Garfield 2022"],
        )
        assert rid is not None

        funds = tmp_db.conn.execute(
            "SELECT funder FROM record_funding WHERE record_id = ? ORDER BY funder",
            (rid,),
        ).fetchall()
        assert {f["funder"] for f in funds} == {
            "NIH R01-67890",
            "NSF Grant #12345",
        }

        refs = tmp_db.conn.execute(
            "SELECT ref_text FROM record_references WHERE record_id = ?", (rid,)
        ).fetchall()
        assert len(refs) == 3

    def test_insert_no_commit_flag(self, tmp_db: CitationDatabase):
        """When _commit=False, the caller controls commit timing.

        SQLite's same-connection visibility means the row is visible
        to this connection's SELECTs immediately, but it will be rolled
        back if the transaction is rolled back.  Verify rollback works
        when _commit=False and the caller does not commit.
        """
        rid = tmp_db.insert_record(
            record_data={"title": "Buffered", "source_database": "T", "source_file": "t"},
            authors=[],
            keywords=[],
            institutions=[],
            _commit=False,
        )
        assert rid is not None
        # Roll back the uncommitted insert
        tmp_db.conn.rollback()
        # After rollback, the row is gone
        assert tmp_db.get_record_count() == 0

        # Now insert again and commit explicitly
        tmp_db.insert_record(
            record_data={"title": "Buffered2", "source_database": "T", "source_file": "t"},
            authors=[],
            keywords=[],
            institutions=[],
            _commit=False,
        )
        tmp_db.conn.commit()
        assert tmp_db.get_record_count() == 1

    def test_insert_serializes_raw_data_dict(self, tmp_db: CitationDatabase):
        """raw_data dict should be JSON-serialized before insert."""
        rid = tmp_db.insert_record(
            record_data={
                "title": "Raw",
                "source_database": "T",
                "source_file": "t",
                "raw_data": {"custom": "value", "score": 42},
            },
            authors=[],
            keywords=[],
            institutions=[],
        )
        row = tmp_db.conn.execute(
            "SELECT raw_data FROM records WHERE id = ?", (rid,)
        ).fetchone()
        # raw_data should be a JSON string
        assert isinstance(row["raw_data"], str)
        assert json.loads(row["raw_data"]) == {"custom": "value", "score": 42}

    def test_insert_sets_imported_at(self, tmp_db: CitationDatabase):
        """imported_at timestamp is auto-populated."""
        before = datetime.utcnow().isoformat()
        rid = tmp_db.insert_record(
            record_data={"title": "T", "source_database": "X", "source_file": "x"},
            authors=[],
            keywords=[],
            institutions=[],
        )
        row = tmp_db.conn.execute(
            "SELECT imported_at FROM records WHERE id = ?", (rid,)
        ).fetchone()
        assert row["imported_at"] is not None
        # Should be recent (>= test start)
        assert row["imported_at"] >= before

    def test_insert_preserves_author_order(self, tmp_db: CitationDatabase):
        """Author order should be preserved in record_authors.author_order."""
        authors = [
            {"full_name": f"Author {i}", "order": i + 1}
            for i in range(5)
        ]
        rid = tmp_db.insert_record(
            record_data={"title": "T", "source_database": "X", "source_file": "x"},
            authors=authors,
            keywords=[],
            institutions=[],
        )
        rows = tmp_db.conn.execute(
            "SELECT full_name, author_order FROM record_authors "
            "WHERE record_id = ? ORDER BY author_order",
            (rid,),
        ).fetchall()
        assert [r["full_name"] for r in rows] == [f"Author {i}" for i in range(5)]

    def test_insert_preserves_is_corresponding(self, tmp_db: CitationDatabase):
        """is_corresponding boolean should be stored as 0/1."""
        rid = tmp_db.insert_record(
            record_data={"title": "T", "source_database": "X", "source_file": "x"},
            authors=[
                {"full_name": "A", "order": 1, "is_corresponding": False},
                {"full_name": "B", "order": 2, "is_corresponding": True},
            ],
            keywords=[],
            institutions=[],
        )
        rows = tmp_db.conn.execute(
            "SELECT full_name, is_corresponding FROM record_authors "
            "WHERE record_id = ? ORDER BY author_order",
            (rid,),
        ).fetchall()
        assert rows[0]["is_corresponding"] == 0
        assert rows[1]["is_corresponding"] == 1

    def test_insert_institution_fields(self, tmp_db: CitationDatabase):
        """All Institution fields (country, province, city, inst_type) are stored."""
        rid = tmp_db.insert_record(
            record_data={"title": "T", "source_database": "X", "source_file": "x"},
            authors=[],
            keywords=[],
            institutions=[
                {
                    "name": "Tsinghua University",
                    "country": "China",
                    "province": "Beijing",
                    "city": "Beijing",
                    "inst_type": "university",
                }
            ],
        )
        row = tmp_db.conn.execute(
            "SELECT * FROM record_institutions WHERE record_id = ?", (rid,)
        ).fetchone()
        assert row["name"] == "Tsinghua University"
        assert row["country"] == "China"
        assert row["province"] == "Beijing"
        assert row["inst_type"] == "university"


# ===========================================================================
# CitationDatabase — clear_records
# ===========================================================================


class TestClearRecords:
    def test_clear_empty_db(self, tmp_db: CitationDatabase):
        """Clearing an empty DB should not raise."""
        tmp_db.clear_records()
        assert tmp_db.get_record_count() == 0

    def test_clear_removes_records(self, tmp_db: CitationDatabase, sample_records):
        """All records should be removed by clear_records()."""
        for r in sample_records[:3]:
            payload = record_to_db_serializable(r)
            tmp_db.insert_record(
                record_data=payload["record_data"],
                authors=payload["authors"],
                keywords=payload["keywords"],
                institutions=payload["institutions"],
            )
        assert tmp_db.get_record_count() == 3
        tmp_db.clear_records()
        assert tmp_db.get_record_count() == 0

    def test_clear_cascades_to_related_tables(
        self, tmp_db: CitationDatabase, sample_records
    ):
        """Related tables (authors, keywords, etc.) should also be cleared."""
        r = sample_records[0]
        payload = record_to_db_serializable(r)
        rid = tmp_db.insert_record(
            record_data=payload["record_data"],
            authors=payload["authors"],
            keywords=payload["keywords"],
            institutions=payload["institutions"],
            funding=["Test Fund"],
            references=["Ref 1"],
        )
        assert rid is not None
        tmp_db.clear_records()

        # All related tables should be empty
        for table in [
            "record_authors",
            "record_keywords",
            "record_institutions",
            "record_funding",
            "record_references",
        ]:
            count = tmp_db.conn.execute(
                f"SELECT COUNT(*) AS c FROM {table}"
            ).fetchone()["c"]
            assert count == 0, f"{table} not cleared"

    def test_clear_preserves_llm_cache(self, tmp_db: CitationDatabase):
        """LLM cache should survive clear_records()."""
        tmp_db.save_llm_cache("key1", "response1", 100, "test-model")
        tmp_db.clear_records()
        # LLM cache still there
        assert tmp_db.get_cached_llm_response("key1") == "response1"


# ===========================================================================
# CitationDatabase — scan_log
# ===========================================================================


class TestScanLog:
    def test_insert_scan_log(self, tmp_db: CitationDatabase):
        """Scan log entries are stored correctly."""
        tmp_db.insert_scan_log(
            filepath="/tmp/test.xlsx",
            source="CNKI",
            record_count=100,
            year_min=2018,
            year_max=2024,
        )
        rows = list(
            tmp_db.conn.execute("SELECT * FROM scan_log ORDER BY id DESC")
        )
        assert len(rows) == 1
        assert rows[0]["filepath"] == "/tmp/test.xlsx"
        assert rows[0]["source"] == "CNKI"
        assert rows[0]["record_count"] == 100

    def test_insert_scan_log_no_years(self, tmp_db: CitationDatabase):
        """Scan log handles None year_min/year_max."""
        tmp_db.insert_scan_log("/tmp/u.txt", "Unknown", 0, None, None)
        rows = list(tmp_db.conn.execute("SELECT * FROM scan_log"))
        assert rows[0]["year_min"] is None


# ===========================================================================
# CitationDatabase — queries
# ===========================================================================


class TestQueries:
    def test_get_all_records_ordered_by_year(self, tmp_db: CitationDatabase, sample_records):
        """Records should be returned in year DESC order."""
        for r in sample_records[:5]:
            payload = record_to_db_serializable(r)
            tmp_db.insert_record(
                record_data=payload["record_data"],
                authors=payload["authors"],
                keywords=payload["keywords"],
                institutions=payload["institutions"],
            )
        rows = tmp_db.get_all_records()
        assert len(rows) == 5
        years = [r["year"] for r in rows if r["year"] is not None]
        assert years == sorted(years, reverse=True)

    def test_get_record_count(self, tmp_db: CitationDatabase):
        """Count should be 0 for empty DB."""
        assert tmp_db.get_record_count() == 0

    def test_get_source_stats(self, tmp_db: CitationDatabase, sample_records):
        """Group by source_database, sorted by count DESC."""
        # sample_records[0]=WoS, [1]=CNKI, [2]=arXiv
        # Insert 2 WoS + 1 CNKI
        tmp_db.insert_record(
            record_data=record_to_db_serializable(sample_records[0])["record_data"],
            authors=record_to_db_serializable(sample_records[0])["authors"],
            keywords=record_to_db_serializable(sample_records[0])["keywords"],
            institutions=record_to_db_serializable(sample_records[0])["institutions"],
        )
        tmp_db.insert_record(
            record_data=record_to_db_serializable(sample_records[0])["record_data"],
            authors=record_to_db_serializable(sample_records[0])["authors"],
            keywords=record_to_db_serializable(sample_records[0])["keywords"],
            institutions=record_to_db_serializable(sample_records[0])["institutions"],
        )
        tmp_db.insert_record(
            record_data=record_to_db_serializable(sample_records[1])["record_data"],
            authors=record_to_db_serializable(sample_records[1])["authors"],
            keywords=record_to_db_serializable(sample_records[1])["keywords"],
            institutions=record_to_db_serializable(sample_records[1])["institutions"],
        )

        stats = tmp_db.get_source_stats()
        # First should be WoS (2 records)
        assert stats[0]["source_database"] == "WoS"
        assert stats[0]["cnt"] == 2
        # Second should be CNKI
        assert stats[1]["source_database"] == "CNKI"
        assert stats[1]["cnt"] == 1


# ===========================================================================
# CitationDatabase — LLM cache
# ===========================================================================


class TestLLMCache:
    def test_save_and_get(self, tmp_db: CitationDatabase):
        """Round-trip: save then get returns the same response."""
        tmp_db.save_llm_cache("k1", "response text", 50, "test-model")
        assert tmp_db.get_cached_llm_response("k1") == "response text"

    def test_get_missing_key(self, tmp_db: CitationDatabase):
        """Missing cache key returns None."""
        assert tmp_db.get_cached_llm_response("nonexistent") is None

    def test_save_replaces_existing(self, tmp_db: CitationDatabase):
        """INSERT OR REPLACE semantics: same key overwrites previous value."""
        tmp_db.save_llm_cache("k1", "first", 10, "m1")
        tmp_db.save_llm_cache("k1", "second", 20, "m2")
        assert tmp_db.get_cached_llm_response("k1") == "second"

    def test_cache_stats(self, tmp_db: CitationDatabase):
        """get_llm_cache_stats returns total count and token sum."""
        tmp_db.save_llm_cache("k1", "r1", 100, "m1")
        tmp_db.save_llm_cache("k2", "r2", 200, "m2")
        tmp_db.save_llm_cache("k3", "r3", 300, "m3")
        stats = tmp_db.get_llm_cache_stats()
        assert stats["cached_entries"] == 3
        assert stats["total_tokens_used"] == 600

    def test_cache_stats_empty(self, tmp_db: CitationDatabase):
        """Empty cache should report 0 entries / 0 tokens."""
        stats = tmp_db.get_llm_cache_stats()
        assert stats["cached_entries"] == 0
        assert stats["total_tokens_used"] == 0

    def test_cache_key_uniqueness(self, tmp_db: CitationDatabase):
        """Different keys are stored independently."""
        tmp_db.save_llm_cache("a", "A", 1, "m")
        tmp_db.save_llm_cache("b", "B", 2, "m")
        assert tmp_db.get_cached_llm_response("a") == "A"
        assert tmp_db.get_cached_llm_response("b") == "B"


# ===========================================================================
# CitationDatabase — close / re-open
# ===========================================================================


class TestDatabaseLifecycle:
    def test_close_then_no_conn(self, tmp_db: CitationDatabase):
        """After close(), internal conn is reset to None."""
        tmp_db.close()
        assert tmp_db._conn is None

    def test_reopen_after_close(self, tmp_path: Path):
        """Database can be closed and reopened; data persists."""
        db = CitationDatabase(tmp_path / "x.db")
        db.initialize()
        db.insert_record(
            record_data={"title": "Persisted", "source_database": "X", "source_file": "x"},
            authors=[],
            keywords=[],
            institutions=[],
        )
        db.close()

        # Reopen
        db2 = CitationDatabase(tmp_path / "x.db")
        db2.initialize()
        assert db2.get_record_count() == 1
        db2.close()


# ===========================================================================
# db_loader — load_records_from_db
# ===========================================================================


class TestLoadRecordsFromDB:
    def test_empty_db_returns_empty(self, tmp_db_path: Path):
        """Empty database returns empty list, no error."""
        records = load_records_from_db(tmp_db_path)
        assert records == []

    def test_nonexistent_db(self, tmp_path: Path):
        """Non-existent DB file: should not raise (db is auto-created)."""
        # load_records_from_db creates the file via initialize()
        # but won't find any records
        records = load_records_from_db(tmp_path / "nope.db")
        assert records == []

    def test_round_trip_single_record(self, tmp_db_path: Path, sample_records):
        """Insert via API, load via API: fields preserved."""
        r = sample_records[0]
        db = CitationDatabase(tmp_db_path)
        payload = record_to_db_serializable(r)
        db.insert_record(
            record_data=payload["record_data"],
            authors=payload["authors"],
            keywords=payload["keywords"],
            institutions=payload["institutions"],
        )
        db.close()

        records = load_records_from_db(tmp_db_path)
        assert len(records) == 1
        loaded = records[0]
        assert loaded.title == r.title
        assert loaded.year == r.year
        assert loaded.doi == r.doi
        assert loaded.journal == r.journal
        assert loaded.citation_count == r.citation_count
        assert loaded.language == r.language
        assert loaded.source_database == r.source_database
        assert len(loaded.authors) == 2
        # All keywords (zh + en) end up in `loaded.keywords` after load
        # (load_records_from_db concatenates them).  The split is lost.
        all_kw = set(loaded.keywords)
        assert "machine learning" in all_kw
        assert "healthcare" in all_kw
        assert "ML" in all_kw
        assert "health" in all_kw
        # doc_type round-trips through enum
        assert loaded.doc_type == r.doc_type

    def test_round_trip_with_en_keywords(self, tmp_db_path: Path):
        """English keywords are stored in keywords_en field."""
        r = Record(
            title="EN Kw Test",
            year=2024,
            keywords=["中文关键词"],
            keywords_en=["english keyword"],
            language="zh",
        )
        db = CitationDatabase(tmp_db_path)
        payload = record_to_db_serializable(r)
        db.insert_record(
            record_data=payload["record_data"],
            authors=payload["authors"],
            keywords=payload["keywords"],
            institutions=payload["institutions"],
        )
        db.close()

        loaded = load_records_from_db(tmp_db_path)[0]
        # Both zh and en keywords end up in `keywords` (the loading code
        # does not split them back).  Verify both are present.
        all_kw = set(loaded.keywords)
        assert "中文关键词" in all_kw
        assert "english keyword" in all_kw

    def test_round_trip_funding_and_refs(self, tmp_db_path: Path):
        """Funding and references survive round-trip."""
        r = Record(
            title="Funded",
            year=2024,
            funding=["Fund A", "Fund B"],
            references=["Ref 1", "Ref 2", "Ref 3"],
        )
        db = CitationDatabase(tmp_db_path)
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

        loaded = load_records_from_db(tmp_db_path)[0]
        assert loaded.funding is not None
        assert set(loaded.funding) == {"Fund A", "Fund B"}
        assert loaded.references is not None
        assert len(loaded.references) == 3

    def test_handles_corrupt_raw_data(self, tmp_db_path: Path, sample_records):
        """Corrupt JSON in raw_data column should not raise (defensive).

        Uses a record with all required integer fields populated so that
        BUG-001 (empty-string int parsing) does not interfere.
        """
        r = sample_records[0]  # year=2024, citation_count=15 (populated)
        db = CitationDatabase(tmp_db_path)
        payload = record_to_db_serializable(r)
        rid = db.insert_record(
            record_data=payload["record_data"],
            authors=payload["authors"],
            keywords=payload["keywords"],
            institutions=payload["institutions"],
        )
        # Manually corrupt the raw_data
        db.conn.execute(
            "UPDATE records SET raw_data = ? WHERE id = ?",
            ("{not valid json", rid),
        )
        db.conn.commit()
        db.close()

        records = load_records_from_db(tmp_db_path)
        # Should not raise; raw_data defaults to {}
        assert len(records) == 1
        assert records[0].raw_data == {}

    def test_handles_null_raw_data(self, tmp_db_path: Path, sample_records):
        """NULL raw_data should not raise.  Uses record with int fields set."""
        r = sample_records[0]
        db = CitationDatabase(tmp_db_path)
        payload = record_to_db_serializable(r)
        rid = db.insert_record(
            record_data=payload["record_data"],
            authors=payload["authors"],
            keywords=payload["keywords"],
            institutions=payload["institutions"],
        )
        db.conn.execute("UPDATE records SET raw_data = NULL WHERE id = ?", (rid,))
        db.conn.commit()
        db.close()

        records = load_records_from_db(tmp_db_path)
        assert records[0].raw_data == {}

    def test_round_trip_many_authors(self, tmp_db_path: Path):
        """Author order is preserved for 10+ authors."""
        authors = [Author(full_name=f"Author {i}", order=i + 1) for i in range(10)]
        r = Record(title="Big collab", year=2024, authors=authors)
        db = CitationDatabase(tmp_db_path)
        payload = record_to_db_serializable(r)
        db.insert_record(
            record_data=payload["record_data"],
            authors=payload["authors"],
            keywords=payload["keywords"],
            institutions=payload["institutions"],
        )
        db.close()

        loaded = load_records_from_db(tmp_db_path)[0]
        assert len(loaded.authors) == 10
        # Order preserved
        assert [a.full_name for a in loaded.authors] == [
            f"Author {i}" for i in range(10)
        ]


# ===========================================================================
# serialization — record_to_db_serializable
# ===========================================================================


class TestRecordToDbSerializable:
    def test_minimal_record(self):
        """Empty record produces all required keys with None/empty values."""
        r = Record(title="Min")
        out = record_to_db_serializable(r)
        assert "record_data" in out
        assert "authors" in out
        assert "keywords" in out
        assert "institutions" in out
        assert "funding" in out
        assert "references" in out

        # record_data fields
        rd = out["record_data"]
        assert rd["title"] == "Min"
        assert rd["source_database"] == ""
        assert rd["year"] is None

        # Empty lists
        assert out["authors"] == []
        assert out["keywords"] == []
        assert out["institutions"] == []

    def test_doc_type_serialized_as_string(self):
        """doc_type enum is converted to its string value."""
        r = Record(title="T", doc_type=DocType.ARTICLE)
        out = record_to_db_serializable(r)
        assert out["record_data"]["doc_type"] == "article"

    def test_keywords_with_lang(self):
        """Chinese keywords get lang='zh', English get lang='en'."""
        r = Record(
            title="T",
            keywords=["机器学习"],
            keywords_en=["machine learning"],
            language="zh",
        )
        out = record_to_db_serializable(r)
        # Chinese keyword tagged with record.language
        assert out["keywords"][0]["keyword"] == "机器学习"
        assert out["keywords"][0]["lang"] == "zh"
        # English keyword tagged 'en'
        assert out["keywords"][1]["keyword"] == "machine learning"
        assert out["keywords"][1]["lang"] == "en"

    def test_keywords_default_lang_zh(self):
        """When language is None, default to 'zh'."""
        r = Record(title="T", keywords=["kw"], language=None)
        out = record_to_db_serializable(r)
        assert out["keywords"][0]["lang"] == "zh"

    def test_no_en_keywords_does_not_add_en(self):
        """When keywords_en is None/empty, don't add 'en' entries."""
        r = Record(title="T", keywords=["a", "b"], keywords_en=None)
        out = record_to_db_serializable(r)
        assert len(out["keywords"]) == 2
        assert all(k["lang"] == "zh" for k in out["keywords"])

    def test_funding_passed_through(self):
        """funding list is passed through as-is."""
        r = Record(title="T", funding=["F1", "F2"])
        out = record_to_db_serializable(r)
        assert out["funding"] == ["F1", "F2"]

    def test_funding_none_preserved(self):
        """funding=None stays None (not converted to [])."""
        r = Record(title="T", funding=None)
        out = record_to_db_serializable(r)
        assert out["funding"] is None

    def test_references_passed_through(self):
        """references list is passed through."""
        r = Record(title="T", references=["R1", "R2"])
        out = record_to_db_serializable(r)
        assert out["references"] == ["R1", "R2"]

    def test_author_dict_has_all_fields(self):
        """Each author dict contains all Author fields."""
        a = Author(
            full_name="Smith, John",
            surname="Smith",
            given_name="John",
            order=1,
            is_corresponding=True,
            affiliation="MIT",
            email="smith@mit.edu",
        )
        r = Record(title="T", authors=[a])
        out = record_to_db_serializable(r)
        ad = out["authors"][0]
        assert ad["full_name"] == "Smith, John"
        assert ad["surname"] == "Smith"
        assert ad["given_name"] == "John"
        assert ad["order"] == 1
        assert ad["is_corresponding"] is True
        assert ad["affiliation"] == "MIT"
        assert ad["email"] == "smith@mit.edu"

    def test_institution_dict_has_all_fields(self):
        """Documents the current serialization behavior for Institution.

        NOTE: As of v4.0.4, `name_en` is NOT included in the serialized
        dict — see BUG-002 in the test report.  This test asserts the
        current (buggy) behavior; will be updated when fixed.
        """
        i = Institution(
            name="MIT",
            name_en="Massachusetts Institute of Technology",
            country="USA",
            province="MA",
            city="Cambridge",
            inst_type="university",
        )
        r = Record(title="T", institutions=[i])
        out = record_to_db_serializable(r)
        id_ = out["institutions"][0]
        assert id_["name"] == "MIT"
        # TODO: assert id_["name_en"] == "..." once BUG-002 is fixed
        assert "name_en" not in id_  # documents current behavior
        assert id_["country"] == "USA"

    def test_record_data_all_fields(self):
        """All Record fields are in record_data dict."""
        r = Record(
            title="T",
            title_en="T (EN)",
            year=2024,
            journal="Nature",
            volume="10",
            issue="3",
            pages="100-110",
            doi="10.1000/x",
            issn="1234-5678",
            abstract="Abstract",
            abstract_en="Abstract EN",
            language="en",
            citation_count=50,
            source_database="WoS",
            source_file="wos.txt",
        )
        out = record_to_db_serializable(r)
        rd = out["record_data"]
        assert rd["title_en"] == "T (EN)"
        assert rd["issn"] == "1234-5678"
        assert rd["abstract_en"] == "Abstract EN"
        assert rd["citation_count"] == 50
        assert rd["source_file"] == "wos.txt"


# ===========================================================================
# Integration — full round-trip with all data
# ===========================================================================


class TestIntegrationRoundTrip:
    def test_full_sample_round_trip(self, tmp_db_path: Path, sample_records):
        """Insert all 10 sample records, load them back, verify counts."""
        db = CitationDatabase(tmp_db_path)
        for r in sample_records:
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

        records = load_records_from_db(tmp_db_path)
        assert len(records) == len(sample_records)
        # Titles preserved
        loaded_titles = {r.title for r in records}
        original_titles = {r.title for r in sample_records}
        assert loaded_titles == original_titles

    def test_batch_insert_performance_smoke(self, tmp_db_path: Path):
        """Smoke test: 100 records insert in reasonable time (<5s)."""
        import time

        db = CitationDatabase(tmp_db_path)
        start = time.time()
        for i in range(100):
            db.insert_record(
                record_data={
                    "title": f"Paper {i}",
                    "source_database": "TestDB",
                    "source_file": "t.txt",
                    "year": 2020 + (i % 5),
                },
                authors=[
                    {"full_name": f"Author {i}", "order": 1},
                    {"full_name": f"Co-author {i}", "order": 2},
                ],
                keywords=[{"keyword": f"kw{i}", "lang": "en"}],
                institutions=[],
                _commit=False,  # batched
            )
        db.conn.commit()
        elapsed = time.time() - start
        assert elapsed < 5.0
        assert db.get_record_count() == 100
        db.close()
