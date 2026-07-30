"""数据管理 API 路由（scan/import/clean/status）。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from citationer.services.data_ops import get_record_count, run_clean, run_import, run_scan
from citationer.web.dependencies import DbDep

router = APIRouter()


@router.get("/status")
def status(db: DbDep) -> dict:
    return {"total_records": get_record_count(db)}


@router.post("/scan")
def scan(db: DbDep) -> dict:
    try:
        run_scan()
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="扫描模块不可用") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/import")
def import_data(db: DbDep) -> dict:
    try:
        run_import()
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="导入模块不可用") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/clean")
def clean(db: DbDep) -> dict:
    try:
        run_clean()
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="清洗模块不可用") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True}
