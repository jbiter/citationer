"""Trend analysis CLI commands — hotspots, strategic diagrams, etc."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from citationer.analysis.trend import TrendEngine
from citationer.utils.db_loader import get_records

app = typer.Typer(
    name="trend",
    help="研究趋势分析",
    no_args_is_help=True,
)

console = Console()


_get_records = get_records


@app.command(name="hotspots")
def hotspots(
    top_n: int = typer.Option(
        30, "--top", "-n", help="分析前 N 个高频关键词"
    ),
    gamma: float = typer.Option(
        1.0, "--gamma", "-g", help="爆发灵敏度（越低越敏感，推荐 0.5~2.0）"
    ),
    min_years: int = typer.Option(
        2, "--min-years", "-y", help="最少持续年数"
    ),
) -> None:
    """关键词突变检测：识别在某段时间内突然高频出现的关键词。"""
    records = _get_records()
    if not records:
        return

    console.print(
        f"[dim]正在分析前 {top_n} 个高频关键词的突变情况…[/dim]"
    )
    engine = TrendEngine(records)
    result = engine.hotspots(top_n=top_n, gamma=gamma, min_years=min_years)

    if not result.bursts:
        console.print("[yellow]未检测到显著的关键词突变[/yellow]")
        return

    # Summary
    rising = [b for b in result.bursts if b.end_year >= 2020]
    console.print()
    console.print(
        f"[bold]检测到 {len(result.bursts)} 个关键词突变[/bold]"
        f" · 其中 {len(rising)} 个近期活跃"
    )
    console.print()

    # Table: top bursts by strength
    table = Table(
        title="🔥 关键词突变检测 (Burst Detection)",
        show_header=True,
        header_style="bold yellow",
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("关键词")
    table.add_column("爆发区间", justify="center")
    table.add_column("强度", justify="right")
    table.add_column("趋势")

    for i, b in enumerate(result.bursts[:20], 1):
        period = f"{b.start_year} – {b.end_year}"
        trend_icon = "📈" if b.end_year >= 2020 else "📉"
        table.add_row(
            str(i),
            b.keyword,
            period,
            f"{b.strength:.1f}×",
            trend_icon,
        )

    console.print(table)

    # Tip
    console.print()
    console.print(
        "[dim]💡 降低 --gamma 可检测更微弱的突变，提高 --gamma 仅检测强突变[/dim]"
    )
