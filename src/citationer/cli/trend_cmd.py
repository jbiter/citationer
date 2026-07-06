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


# ------------------------------------------------------------------
# trend strategy
# ------------------------------------------------------------------


@app.command(name="strategy")
def strategy(
    top_n: int = typer.Option(
        50, "--top", "-n", help="分析前 N 个高频关键词"
    ),
) -> None:
    """战略坐标图：关键词聚类后按向心度和密度绘制四象限主题图。"""
    records = _get_records()
    if not records:
        return

    console.print("[dim]正在构建关键词共现网络并计算战略坐标…[/dim]")
    engine = TrendEngine(records)
    result = engine.strategy(top_n=top_n)

    if not result.themes:
        console.print("[yellow]数据不足以生成战略坐标图[/yellow]")
        return

    quadrant_names = {
        1: "🚀 主流主题 (Motor)",
        2: "🔬 边缘主题 (Niche)",
        3: "🌱 新兴/衰退 (Emerging)",
        4: "📚 基础主题 (Basic)",
    }

    # Summary
    console.print()
    console.print(
        f"[bold]战略坐标图[/bold] · "
        f"{len(result.themes)} 个主题 · "
        f"向心度中值: {result.centrality_median} · "
        f"密度中值: {result.density_median}"
    )

    # Table
    table = Table(
        title="🎯 主题战略定位",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("主题")
    table.add_column("核心关键词")
    table.add_column("向心度", justify="right")
    table.add_column("密度", justify="right")
    table.add_column("象限")

    for i, t in enumerate(result.themes[:15], 1):
        kw_str = ", ".join(t.keywords[:3])
        table.add_row(
            str(i), t.label, kw_str,
            f"{t.centrality:.3f}", f"{t.density:.3f}",
            quadrant_names.get(t.quadrant, f"Q{t.quadrant}"),
        )

    console.print(table)

    # Terminal scatter plot
    _plot_strategy_quadrant(result)


def _plot_strategy_quadrant(result) -> None:
    """Render a terminal scatter plot of the strategic diagram."""
    if not result.themes:
        return

    try:
        import plotext as plt
    except ImportError:
        return

    plt.clf()
    plt.plotsize(70, 18)

    quad_colors = {1: "green", 2: "blue", 3: "red", 4: "yellow"}

    for t in result.themes:
        plt.scatter(
            [t.centrality], [t.density],
            label=t.label[:12],
            color=quad_colors.get(t.quadrant, "gray"),
        )

    # Quadrant lines
    plt.vline(result.centrality_median, color="gray")
    plt.hline(result.density_median, color="gray")

    plt.title("Strategic Diagram")
    plt.xlabel("Centrality (向心度)")
    plt.ylabel("Density (密度)")

    import re
    _sgr_re = re.compile(r"\x1b\[[0-9;]*m")
    chart = plt.build()
    if chart:
        print(_sgr_re.sub("", chart))


# ------------------------------------------------------------------
# trend river
# ------------------------------------------------------------------


@app.command(name="river")
def river(
    top_n: int = typer.Option(
        8, "--top", "-n", help="追踪前 N 个关键词"
    ),
    window: int = typer.Option(
        5, "--window", "-w", help="时间窗口大小（年）"
    ),
) -> None:
    """主题河流图：追踪关键词热度随时间的演化。"""
    records = _get_records()
    if not records:
        return

    console.print("[dim]正在计算关键词时间演化…[/dim]")
    engine = TrendEngine(records)
    result = engine.river(top_n=top_n, window=window)

    if not result.keywords:
        console.print("[yellow]数据不足以生成河流图[/yellow]")
        return

    # Table
    table = Table(
        title=f"🌊 关键词演化 (窗口={window}年)",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("关键词", style="dim")
    for w in result.windows:
        table.add_column(w, justify="right")

    for kw in result.keywords[:12]:
        shares = result.matrix.get(kw, [])
        row = [kw]
        for s in shares:
            row.append(f"{s:.1f}%" if s > 0 else "-")
        table.add_row(*row)

    console.print(table)

    # Terminal stacked bar chart
    _plot_river(result)


def _plot_river(result) -> None:
    """Render a stacked bar chart for the thematic river."""
    if not result.keywords or not result.windows:
        return

    try:
        import plotext as plt
    except ImportError:
        return

    plt.clf()
    plt.plotsize(80, min(20, len(result.keywords) + 6))

    # Build stacked bars
    x_indices = list(range(len(result.windows)))
    bottom = [0.0] * len(result.windows)

    for kw in result.keywords[:8]:
        shares = result.matrix.get(kw, [])
        if not shares:
            continue
        # Pad if needed
        while len(shares) < len(result.windows):
            shares.append(0.0)
        plt.bar(
            x_indices, shares, bottom=bottom,
            label=kw[:15],
            orientation="v",
        )
        bottom = [b + s for b, s in zip(bottom, shares)]

    plt.xticks(x_indices, result.windows)
    plt.title("Thematic River")
    plt.xlabel("Time Window")
    plt.ylabel("Share (%)")

    import re
    _sgr_re = re.compile(r"\x1b\[[0-9;]*m")
    chart = plt.build()
    if chart:
        print(_sgr_re.sub("", chart))
