"""数据管理 API 路由（scan/import/clean/status）。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from citationer.services.data_ops import get_record_count, run_clean, run_import, run_scan
from citationer.web.dependencies import DbDep

router = APIRouter()


def _require_safe_request(
    x_requested_with: Annotated[str | None, Header()] = None,
) -> None:
    """状态变更接口要求前端带自定义头，防止 CSRF。"""
    if x_requested_with != "XMLHttpRequest":
        raise HTTPException(
            status_code=403,
            detail="状态变更请求需要 X-Requested-With: XMLHttpRequest 头",
        )


@router.get("/status")
def status(db: DbDep) -> dict:
    return {"total_records": get_record_count(db)}


@router.post("/scan")
def scan(
    _safe: Annotated[None, Depends(_require_safe_request)],
) -> dict:
    try:
        run_scan()
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="扫描模块不可用") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/import")
def import_data(
    _safe: Annotated[None, Depends(_require_safe_request)],
) -> dict:
    try:
        run_import()
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="导入模块不可用") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/clean")
def clean(
    _safe: Annotated[None, Depends(_require_safe_request)],
) -> dict:
    try:
        run_clean()
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="清洗模块不可用") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"ok": True}
