"""FastAPI 依赖项。"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException

from citationer.utils.config import get_db_path
from citationer.utils.database import CitationDatabase
from citationer.utils.db_loader import load_records_from_db


def _db_path() -> Path:
    return get_db_path()


def get_db() -> CitationDatabase:
    """返回当前工作目录下已初始化的 CitationDatabase。"""
    db = CitationDatabase(_db_path())
    db.initialize()
    return db


def get_records() -> list:
    """从本地数据库加载记录；未导入时返回 400。"""
    records = load_records_from_db(_db_path())
    if not records:
        raise HTTPException(
            status_code=400,
            detail="尚未导入记录。请先运行 'citationer import'。",
        )
    return records


DbDep = Annotated[CitationDatabase, Depends(get_db)]
RecordsDep = Annotated[list, Depends(get_records)]
