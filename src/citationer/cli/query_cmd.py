"""P5-10: `citationer query` — DSL filter on imported records.

Usage:
    citationer query "year>=2020 AND journal='Nature'"
    citationer query "language='en' OR language='zh'" --format json
    citationer query "keyword='machine learning'" --limit 50 --output q.json

The DSL is intentionally narrow (no `eval()`).  See
`citationer.utils.query.parse_filter` for the grammar.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from citationer.utils.db_loader import get_records
from citationer.utils.query import matches, parse_filter

app = typer.Typer(
    name="query",
    help="按字段过滤导入的记录（DSL 过滤）",
    no_args_is_help=True,
)

console = Console()

_get_records = get_records


@app.command(name="query")
def query_cmd(
    filter_expr: str = typer.Argument(..., help="过滤表达式，如 'year>=2020 AND journal=Nature'"),
    fmt: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="输出格式: table, json, csv",
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="输出文件路径"),
    limit: int | None = typer.Option(None, "--limit", "-n", help="最多输出 N 条"),
) -> None:
    """Filter imported records with a small DSL and dump the result."""
    try:
        filters = parse_filter(filter_expr)
    except ValueError as e:
        console.print(f"[red]❌ 解析失败: {e}[/red]")
        raise typer.Exit(1) from e

    records = _get_records()
    if not records:
        return

    matched = [r for r in records if matches(r, filters)]
    if limit is not None and limit > 0:
        matched = matched[:limit]

    if not matched:
        console.print(f"[dim]无匹配记录（共 {len(records)} 条）[/dim]")
        return

    if fmt == "json":
        _write_json(matched, output)
    elif fmt == "csv":
        _write_csv(matched, output)
    else:
        _write_table(matched)


def _write_table(records: list) -> None:
    table = Table(title=f"📊 匹配记录 (共 {len(records)} 条)")
    table.add_column("#", justify="right", style="dim")
    table.add_column("标题", style="cyan")
    table.add_column("年份", justify="center")
    table.add_column("期刊")
    table.add_column("作者数", justify="right")
    table.add_column("引用数", justify="right")
    for i, r in enumerate(records, 1):
        title_short = r.title[:60] + "…" if len(r.title) > 60 else r.title
        table.add_row(
            str(i),
            title_short,
            str(r.year) if r.year else "-",
            r.journal or "-",
            str(len(r.authors)),
            str(r.citation_count) if r.citation_count is not None else "-",
        )
    console.print(table)


def _write_json(records: list, output: Path | None) -> None:
    payload = [_record_to_dict(r) for r in records]
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        console.print(f"[green]✅ 已写入 {len(records)} 条记录到 {output}[/green]")
    else:
        console.print(text)


def _write_csv(records: list, output: Path | None) -> None:
    rows = [_record_to_dict(r) for r in records]
    fieldnames = ["title", "year", "journal", "authors", "citation_count", "language"]
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in rows:
                r["authors"] = "; ".join(r.get("authors", []))
                writer.writerow(r)
        console.print(f"[green]✅ 已写入 {len(records)} 条记录到 {output}[/green]")
    else:
        writer = csv.DictWriter(
            console.file, fieldnames=fieldnames, extrasaction="ignore"
        )
        writer.writeheader()
        for r in rows:
            r["authors"] = "; ".join(r.get("authors", []))
            writer.writerow(r)


def _record_to_dict(r) -> dict[str, Any]:
    return {
        "title": r.title,
        "year": r.year,
        "journal": r.journal,
        "authors": [a.full_name for a in r.authors],
        "citation_count": r.citation_count,
        "language": r.language,
        "doc_type": r.doc_type.value if r.doc_type else None,
        "keywords": list(r.keywords),
    }
