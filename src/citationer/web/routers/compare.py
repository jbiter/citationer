"""多数据集对比 API 路由。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from citationer.analysis.compare import CompareEngine
from citationer.web.dependencies import RecordsDep
from citationer.web.serializers import to_json_safe

router = APIRouter()


def _engine(records: list, by: str) -> CompareEngine:
    return CompareEngine(records, by=by)


@router.get("/overview")
def overview(
    records: RecordsDep,
    by: Annotated[str, Query(pattern="^(database|file)$")] = "database",
    top_n: Annotated[int, Query(ge=1, le=200)] = 10,
    threshold: Annotated[float, Query(ge=0.0, le=1.0)] = 0.85,
) -> dict:
    overviews, overlaps = _engine(records, by).overview(top_n=top_n, threshold=threshold)
    return to_json_safe({
        "overviews": {k: v for k, v in overviews.items()},
        "overlaps": overlaps,
    })


@router.get("/trends")
def trends(
    records: RecordsDep,
    by: Annotated[str, Query(pattern="^(database|file)$")] = "database",
) -> dict:
    return to_json_safe(_engine(records, by).trends())


@router.get("/topics")
def topics(
    records: RecordsDep,
    by: Annotated[str, Query(pattern="^(database|file)$")] = "database",
    top_n: Annotated[int, Query(ge=1, le=200)] = 20,
) -> dict:
    return to_json_safe(_engine(records, by).topics(top_n=top_n))


@router.get("/network")
def network(
    records: RecordsDep,
    by: Annotated[str, Query(pattern="^(database|file)$")] = "database",
    collab_type: Annotated[str, Query(pattern="^(authors|institutions)$")] = "authors",
    min_papers: Annotated[int, Query(ge=1)] = 2,
) -> dict:
    return to_json_safe(_engine(records, by).network(collab_type=collab_type, min_papers=min_papers))
