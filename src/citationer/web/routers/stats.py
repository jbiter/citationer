"""Stats API 路由。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from citationer.analysis.stats import StatsEngine
from citationer.web.dependencies import RecordsDep
from citationer.web.serializers import to_json_safe

router = APIRouter()


def _engine(records: list) -> StatsEngine:
    return StatsEngine(records)


@router.get("/overview")
def overview(records: RecordsDep) -> dict:
    return to_json_safe(_engine(records).overview())


@router.get("/yearly")
def yearly(records: RecordsDep) -> dict:
    return to_json_safe(_engine(records).yearly())


@router.get("/journals")
def journals(
    records: RecordsDep,
    top: Annotated[int, Query(ge=1, le=200)] = 20,
) -> dict:
    return to_json_safe(_engine(records).journals(top_n=top))


@router.get("/authors")
def authors(
    records: RecordsDep,
    top: Annotated[int, Query(ge=1, le=200)] = 20,
) -> dict:
    return to_json_safe(_engine(records).authors(top_n=top))


@router.get("/institutions")
def institutions(
    records: RecordsDep,
    top: Annotated[int, Query(ge=1, le=200)] = 20,
) -> dict:
    return to_json_safe(_engine(records).institutions(top_n=top))


@router.get("/funding")
def funding(
    records: RecordsDep,
    top: Annotated[int, Query(ge=1, le=200)] = 20,
) -> dict:
    return to_json_safe(_engine(records).funding(top_n=top))
