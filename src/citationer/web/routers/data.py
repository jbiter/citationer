"""数据管理 API 路由（scan/import/clean/status）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from citationer.utils.config import get_db_path
from citationer.utils.db_loader import load_records_from_db
from citationer.web.dependencies import DbDep

router = APIRouter()


@router.get("/status")
def status(db: DbDep) -> dict:
    records = load_records_from_db(get_db_path())
    return {"total_records": len(records)}


@router.post("/scan")
def scan(db: DbDep) -> dict:
    try:
        from citationer.cli.scan_cmd import scan as _scan
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="扫描模块不可用") from exc
    _scan()
    return {"ok": True}


@router.post("/import")
def import_data(db: DbDep) -> dict:
    try:
        from citationer.cli.import_cmd import import_data as _import
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="导入模块不可用") from exc
    _import()
    return {"ok": True}


@router.post("/clean")
def clean(db: DbDep) -> dict:
    try:
        from citationer.cli.clean_cmd import clean as _clean
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="清洗模块不可用") from exc
    _clean()
    return {"ok": True}
