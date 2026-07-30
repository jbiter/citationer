"""图表生成 API 路由。"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi import Path as PathParam
from fastapi.responses import FileResponse

from citationer.analysis.stats import StatsEngine
from citationer.web.dependencies import RecordsDep

router = APIRouter()


def _require_viz_charts():
    """确保可视化依赖可用，否则返回 501。"""
    try:
        import matplotlib

        matplotlib.use("Agg")
        from citationer.viz import charts as viz_charts
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="需要 viz extras") from exc
    return viz_charts


def _require_network_engine():
    """确保网络分析依赖可用，否则返回 501。"""
    try:
        import networkx  # noqa: F401
        import plotly.graph_objects  # noqa: F401

        from citationer.analysis.network import NetworkEngine
    except ImportError as exc:
        raise HTTPException(
            status_code=501,
            detail="Network 分析需要 [network] extras：pip install 'citationer[network]'",
        ) from exc
    return NetworkEngine


def _write_empty_html(path: Path, title: str) -> Path:
    """为空的网络图生成占位 HTML。"""
    path.write_text(
        f"<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>{title}</title></head>"
        f"<body><h1>{title}</h1><p>数据不足，无法生成网络图。</p></body></html>",
        encoding="utf-8",
    )
    return path


@router.get("/yearly.png")
def yearly_chart(
    records: RecordsDep,
    cumulative: bool = False,
) -> FileResponse:
    viz_charts = _require_viz_charts()

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        viz_charts.generate_yearly_chart(
            records,
            Path(tmp.name),
            title="Yearly Publications",
            cumulative=cumulative,
        )
        return FileResponse(tmp.name, media_type="image/png")


@router.get("/top/{kind}.png")
def top_chart(
    records: RecordsDep,
    kind: Annotated[str, PathParam(pattern="^(journals|authors|institutions)$")],
    top: Annotated[int, Query(ge=1, le=200)] = 20,
) -> FileResponse:
    viz_charts = _require_viz_charts()

    engine = StatsEngine(records)
    if kind == "journals":
        data = engine.journals(top_n=top)
        title, xlabel = "Top Journals", "Journal"
    elif kind == "authors":
        data = engine.authors(top_n=top).top_authors
        title, xlabel = "Top Authors", "Author"
    else:
        data = engine.institutions(top_n=top)
        title, xlabel = "Top Institutions", "Institution"

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        viz_charts.generate_top_n_chart(
            data.items,
            Path(tmp.name),
            title=title,
            xlabel=xlabel,
            horizontal=True,
        )
        return FileResponse(tmp.name, media_type="image/png")


@router.get("/network/{kind}.html")
def network_html(
    records: RecordsDep,
    kind: Annotated[str, PathParam(pattern="^(keywords|coauthors|cocitation|coupling)$")],
    top_n: Annotated[int, Query(ge=1, le=200)] = 50,
) -> FileResponse:
    network_engine_cls = _require_network_engine()

    engine = network_engine_cls(records)
    if kind == "keywords":
        result = engine.keyword_cooccurrence(top_n=top_n, threshold=3)
        edges = result.edges
        nodes = [(kw, 1) for kw in result.keywords]
        communities = getattr(result, "communities", {})
    elif kind == "coauthors":
        result = engine.author_collaboration(min_papers=2, collab_type="authors")
        edges = result.edges
        nodes = result.nodes
        communities = getattr(result, "communities", {})
    elif kind == "cocitation":
        result = engine.co_citation(top_n=top_n)
        edges = result.edges
        nodes = None
        communities = {}
    else:
        result = engine.bibliographic_coupling(top_n=top_n)
        edges = result.edges
        nodes = None
        communities = {}

    title = f"{kind} network"
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        output_path = Path(tmp.name)
        if not edges and not nodes:
            _write_empty_html(output_path, title)
        else:
            network_engine_cls.to_html(edges, nodes, communities, output_path, title=title)
        return FileResponse(tmp.name, media_type="text/html")
