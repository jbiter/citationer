"""P5-1: `citationer compare` — multi-dataset comparison commands."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from citationer.analysis.compare import CompareEngine
from citationer.utils.db_loader import get_records

app = typer.Typer(
    name="compare",
    help="多数据集对比分析",
    no_args_is_help=True,
)

console = Console()
_get_records = get_records


def _validate_format(value: str) -> str:
    allowed = {"table", "json", "csv"}
    if value not in allowed:
        raise typer.BadParameter(f"格式必须是 {allowed} 之一")
    return value


def _load_engine(by: str) -> CompareEngine | None:
    records = _get_records()
    if not records:
        console.print("[yellow]⚠ 数据库中没有记录[/yellow]")
        return None
    engine = CompareEngine(records, by=by)
    if len(engine.dataset_names) < 2:
        console.print(
            "[yellow]⚠ 至少需要两个数据集才能进行对比"
            f"（当前仅检测到 {len(engine.dataset_names)} 个）[/yellow]"
        )
        return None
    return engine


def _write_output(data: Any, fmt: str, output: Path | None) -> None:
    if fmt == "json":
        text = _to_json(data)
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding="utf-8")
            console.print(f"[green]✅ 已写入 {output}[/green]")
        else:
            console.print(text)
    elif fmt == "csv":
        rows, fieldnames = _to_csv_rows(data)
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            with open(output, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
            console.print(f"[green]✅ 已写入 {output}[/green]")
        else:
            writer = csv.DictWriter(console.file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
    else:
        _write_table(data)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


@app.command(name="overview")
def overview(
    by: str = typer.Option("database", "--by", help="分组方式: database, file"),
    top_n: int = typer.Option(10, "--top-n", "-n", help="Top-N 期刊/作者/关键词"),
    threshold: float = typer.Option(
        0.85, "--threshold", "-t", help="标题模糊匹配阈值 (0-1)"
    ),
    fmt: str = typer.Option(
        "table", "--format", "-f",
        help="输出格式: table, json, csv",
        callback=_validate_format,
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="输出文件路径"),
) -> None:
    """数据集概览与重叠分析。"""
    engine = _load_engine(by)
    if engine is None:
        return
    overviews, overlaps = engine.overview(top_n=top_n, threshold=threshold)
    data = {"overviews": overviews, "overlaps": overlaps}
    _write_output(data, fmt, output)


@app.command(name="trends")
def trends(
    by: str = typer.Option("database", "--by", help="分组方式: database, file"),
    fmt: str = typer.Option(
        "table", "--format", "-f",
        help="输出格式: table, json, csv",
        callback=_validate_format,
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="输出文件路径"),
) -> None:
    """数据集年度趋势对比。"""
    engine = _load_engine(by)
    if engine is None:
        return
    data = engine.trends()
    _write_output(data, fmt, output)


@app.command(name="topics")
def topics(
    by: str = typer.Option("database", "--by", help="分组方式: database, file"),
    top_n: int = typer.Option(20, "--top-n", "-n", help="每个数据集 Top-N 关键词"),
    fmt: str = typer.Option(
        "table", "--format", "-f",
        help="输出格式: table, json, csv",
        callback=_validate_format,
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="输出文件路径"),
) -> None:
    """数据集关键词/主题对比。"""
    engine = _load_engine(by)
    if engine is None:
        return
    data = engine.topics(top_n=top_n)
    _write_output(data, fmt, output)


@app.command(name="network")
def network(
    by: str = typer.Option("database", "--by", help="分组方式: database, file"),
    collab_type: str = typer.Option(
        "authors", "--type", "-t", help="网络类型: authors, institutions"
    ),
    min_papers: int = typer.Option(
        2, "--min-papers", "-m", help="节点最少发文数"
    ),
    fmt: str = typer.Option(
        "table", "--format", "-f",
        help="输出格式: table, json, csv",
        callback=_validate_format,
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="输出文件路径"),
) -> None:
    """数据集作者/机构网络对比。"""
    engine = _load_engine(by)
    if engine is None:
        return
    data = engine.network(collab_type=collab_type, min_papers=min_papers)
    _write_output(data, fmt, output)


# ---------------------------------------------------------------------------
# Table renderers
# ---------------------------------------------------------------------------


def _write_table(data: Any) -> None:
    if isinstance(data, dict) and "overviews" in data and "overlaps" in data:
        _write_overview_table(data["overviews"], data["overlaps"])
    elif hasattr(data, "year_counts"):
        _write_trends_table(data)
    elif hasattr(data, "dataset_keywords"):
        _write_topics_table(data)
    elif hasattr(data, "shared_nodes"):
        _write_network_table(data)


def _write_overview_table(overviews: dict, overlaps: list) -> None:
    table = Table(title="📊 数据集概览")
    table.add_column("数据集", style="cyan")
    table.add_column("记录数", justify="right")
    table.add_column("年份范围")
    table.add_column("期刊数", justify="right")
    table.add_column("作者数", justify="right")
    table.add_column("关键词数", justify="right")
    for name in sorted(overviews):
        o = overviews[name]
        year_range = f"{o.year_min}-{o.year_max}" if o.year_min else "-"
        table.add_row(
            name,
            str(o.total_records),
            year_range,
            str(o.unique_journals),
            str(o.unique_authors),
            str(o.unique_keywords),
        )
    console.print(table)

    if overlaps:
        ov = Table(title="🔗 数据集两两重叠")
        ov.add_column("数据集 A", style="cyan")
        ov.add_column("数据集 B", style="cyan")
        ov.add_column("DOI 重叠", justify="right")
        ov.add_column("标题重叠", justify="right")
        ov.add_column("关键词 Jaccard", justify="right")
        ov.add_column("共享作者")
        ov.add_column("共享机构")
        for r in overlaps:
            ov.add_row(
                r.dataset_a,
                r.dataset_b,
                str(r.doi_overlap),
                str(r.title_overlap),
                f"{r.keyword_jaccard:.3f}",
                str(len(r.shared_authors)),
                str(len(r.shared_institutions)),
            )
        console.print(ov)


def _write_trends_table(data) -> None:
    if not data.year_counts:
        return
    years = sorted({y for counts in data.year_counts.values() for y in counts})
    table = Table(title="📈 年度趋势对比")
    table.add_column("年份", justify="center")
    for name in sorted(data.year_counts):
        table.add_column(name, justify="right")
    for year in years:
        row = [str(year)]
        for name in sorted(data.year_counts):
            row.append(str(data.year_counts[name].get(year, 0)))
        table.add_row(*row)
    console.print(table)

    slope_table = Table(title="趋势斜率")
    slope_table.add_column("数据集", style="cyan")
    slope_table.add_column("斜率", justify="right")
    for name, slope in sorted(data.slopes.items()):
        slope_table.add_row(name, f"{slope:.2f}")
    console.print(slope_table)


def _write_topics_table(data) -> None:
    table = Table(title="🔤 关键词 Top-N")
    table.add_column("数据集", style="cyan")
    table.add_column("关键词")
    table.add_column("频次", justify="right")
    for name in sorted(data.dataset_keywords):
        for kw, cnt in data.dataset_keywords[name]:
            table.add_row(name, kw, str(cnt))
    console.print(table)

    if data.pairwise_jaccard:
        jt = Table(title="关键词 Jaccard 重叠")
        jt.add_column("数据集 A", style="cyan")
        jt.add_column("数据集 B", style="cyan")
        jt.add_column("Jaccard", justify="right")
        jt.add_column("共享关键词数", justify="right")
        for (a, b), score in data.pairwise_jaccard.items():
            shared = data.shared_keywords.get((a, b), [])
            jt.add_row(a, b, f"{score:.3f}", str(len(shared)))
        console.print(jt)


def _write_network_table(data) -> None:
    table = Table(title=f"🕸️  {data.collab_type} 节点数")
    table.add_column("数据集", style="cyan")
    table.add_column("节点数", justify="right")
    for name, cnt in sorted(data.dataset_node_counts.items()):
        table.add_row(name, str(cnt))
    console.print(table)

    if data.shared_nodes:
        st = Table(title="跨数据集共享节点")
        st.add_column("数据集", style="cyan")
        st.add_column("节点")
        st.add_column("出现次数", justify="right")
        for name in sorted(data.shared_nodes):
            for node, cnt in data.shared_nodes[name]:
                st.add_row(name, node, str(cnt))
        console.print(st)

    if data.cross_edges:
        et = Table(title="跨数据集合作边")
        et.add_column("节点 A", style="cyan")
        et.add_column("节点 B", style="cyan")
        et.add_column("权重", justify="right")
        for a, b, w in data.cross_edges[:20]:
            et.add_row(a, b, str(w))
        console.print(et)


# ---------------------------------------------------------------------------
# JSON / CSV serialization
# ---------------------------------------------------------------------------


def _to_json(data: Any) -> str:
    payload = _serialize(data)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _serialize(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _serialize(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {_serialize_key(k): _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    if isinstance(obj, set):
        return sorted(obj)
    return obj


def _serialize_key(key: Any) -> str:
    if isinstance(key, tuple):
        return "|".join(str(k) for k in key)
    return str(key)


def _to_csv_rows(data: Any) -> tuple[list[dict[str, Any]], list[str]]:
    if isinstance(data, dict) and "overviews" in data and "overlaps" in data:
        return _overview_csv_rows(data["overviews"], data["overlaps"])
    if hasattr(data, "year_counts"):
        return _trends_csv_rows(data)
    if hasattr(data, "dataset_keywords"):
        return _topics_csv_rows(data)
    if hasattr(data, "shared_nodes"):
        return _network_csv_rows(data)
    return [], []


def _overview_csv_rows(overviews: dict, overlaps: list) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    for name in sorted(overviews):
        o = overviews[name]
        rows.append(
            {
                "section": "overview",
                "dataset_a": name,
                "dataset_b": "",
                "metric": "",
                "value": "",
                "total_records": o.total_records,
                "year_min": o.year_min,
                "year_max": o.year_max,
                "unique_journals": o.unique_journals,
                "unique_authors": o.unique_authors,
                "unique_keywords": o.unique_keywords,
            }
        )
    for r in overlaps:
        rows.append(
            {
                "section": "overlap",
                "dataset_a": r.dataset_a,
                "dataset_b": r.dataset_b,
                "metric": "doi_overlap",
                "value": r.doi_overlap,
            }
        )
        rows.append(
            {
                "section": "overlap",
                "dataset_a": r.dataset_a,
                "dataset_b": r.dataset_b,
                "metric": "title_overlap",
                "value": r.title_overlap,
            }
        )
        rows.append(
            {
                "section": "overlap",
                "dataset_a": r.dataset_a,
                "dataset_b": r.dataset_b,
                "metric": "keyword_jaccard",
                "value": r.keyword_jaccard,
            }
        )
    return rows, [
        "section",
        "dataset_a",
        "dataset_b",
        "metric",
        "value",
        "total_records",
        "year_min",
        "year_max",
        "unique_journals",
        "unique_authors",
        "unique_keywords",
    ]


def _trends_csv_rows(data) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    years = sorted({y for counts in data.year_counts.values() for y in counts})
    for year in years:
        row: dict[str, Any] = {"year": year}
        for name in sorted(data.year_counts):
            row[name] = data.year_counts[name].get(year, 0)
        rows.append(row)
    for name, slope in sorted(data.slopes.items()):
        rows.append({"year": "slope", name: slope})
    fieldnames = ["year", *sorted(data.year_counts)]
    return rows, fieldnames


def _topics_csv_rows(data) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    for name in sorted(data.dataset_keywords):
        for rank, (kw, cnt) in enumerate(data.dataset_keywords[name], 1):
            rows.append(
                {
                    "section": "top_keywords",
                    "dataset_a": name,
                    "rank": rank,
                    "keyword": kw,
                    "count": cnt,
                }
            )
    for (a, b), score in data.pairwise_jaccard.items():
        rows.append(
            {
                "section": "jaccard",
                "dataset_a": a,
                "dataset_b": b,
                "jaccard": score,
                "shared_count": len(data.shared_keywords.get((a, b), [])),
            }
        )
    return rows, [
        "section",
        "dataset_a",
        "dataset_b",
        "rank",
        "keyword",
        "count",
        "jaccard",
        "shared_count",
    ]


def _network_csv_rows(data) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    for name, cnt in sorted(data.dataset_node_counts.items()):
        rows.append(
            {"section": "node_counts", "dataset": name, "node": "", "count": cnt}
        )
    for name in sorted(data.shared_nodes):
        for node, cnt in data.shared_nodes[name]:
            rows.append(
                {"section": "shared_nodes", "dataset": name, "node": node, "count": cnt}
            )
    for a, b, w in data.cross_edges:
        rows.append(
            {"section": "cross_edges", "node_a": a, "node_b": b, "weight": w}
        )
    return rows, [
        "section",
        "dataset",
        "node",
        "node_a",
        "node_b",
        "count",
        "weight",
    ]
