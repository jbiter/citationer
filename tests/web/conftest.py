"""Web API 测试 fixture。"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from citationer.models.record import Author, Record
from citationer.utils.database import CitationDatabase
from citationer.utils.serialization import record_to_db_serializable
from citationer.web.app import create_app


@pytest.fixture
def web_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """提供已 seeded 5 条记录的 TestClient。"""
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / ".citationer" / "cache.db"
    db = CitationDatabase(db_path)
    db.initialize()
    db.close()

    records = [
        Record(
            title=f"Paper {i}",
            year=2020 + i,
            doi=f"10.1000/test{i}",
            authors=[Author(full_name=f"Author {i}", order=1)],
            keywords=[f"kw{i}"],
            journal=f"Journal {i % 3}",
            source_database="TestDB",
        )
        for i in range(5)
    ]

    for record in records:
        payload = record_to_db_serializable(record)
        db = CitationDatabase(db_path)
        db.insert_record(
            record_data=payload["record_data"],
            authors=payload["authors"],
            keywords=payload["keywords"],
            institutions=payload["institutions"],
            funding=payload["funding"],
            references=payload["references"],
        )
        db.close()

    yield TestClient(create_app())


@pytest.fixture
def empty_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """提供已初始化但为空数据库的 TestClient。"""
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / ".citationer" / "cache.db"
    db = CitationDatabase(db_path)
    db.initialize()
    db.close()
    yield TestClient(create_app())
