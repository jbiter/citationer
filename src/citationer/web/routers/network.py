"""Network 分析 API 路由。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from citationer.web.dependencies import RecordsDep
from citationer.web.serializers import to_json_safe

router = APIRouter()


def _engine(records: list):
    try:
        import networkx  # noqa: F401
        import plotly.graph_objects  # noqa: F401

        from citationer.analysis.network import NetworkEngine
    except ImportError as exc:
        raise HTTPException(
            status_code=501,
            detail="Network 分析需要 [network] extras：pip install 'citationer[network]'",
        ) from exc
    return NetworkEngine(records)


@router.get("/keywords")
def keyword_cooccurrence(
    records: RecordsDep,
    top_n: Annotated[int, Query(ge=1, le=200)] = 50,
    threshold: Annotated[int, Query(ge=1)] = 3,
) -> dict:
    return to_json_safe(_engine(records).keyword_cooccurrence(top_n=top_n, threshold=threshold))


@router.get("/coauthors")
def author_collaboration(
    records: RecordsDep,
    min_papers: Annotated[int, Query(ge=1)] = 2,
    collab_type: Annotated[str, Query(pattern="^(authors|institutions)$")] = "authors",
) -> dict:
    result = _engine(records).author_collaboration(
        min_papers=min_papers, collab_type=collab_type
    )
    return to_json_safe(result)


@router.get("/cocitation")
def co_citation(
    records: RecordsDep,
    top_n: Annotated[int, Query(ge=1, le=200)] = 30,
) -> dict:
    return to_json_safe(_engine(records).co_citation(top_n=top_n))


@router.get("/coupling")
def bibliographic_coupling(
    records: RecordsDep,
    top_n: Annotated[int, Query(ge=1, le=200)] = 30,
) -> dict:
    return to_json_safe(_engine(records).bibliographic_coupling(top_n=top_n))
