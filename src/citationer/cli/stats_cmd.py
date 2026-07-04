"""Stats commands — descriptive statistical analysis."""

from __future__ import annotations

import sys

import typer
from rich.console import Console
from rich.table import Table

from citationer.analysis.stats import StatsEngine
from citationer.utils.config import get_db_path
from citationer.utils.db_loader import load_records_from_db
from citationer.viz.terminal_charts import plot_hbar, plot_line, plot_line_dual

app = typer.Typer(
    name="stats",
    help="描述性统计分析",
    no_args_is_help=True,
)

console = Console()


def _get_records() -> list:
    """Load records from DB, returning empty list if not available."""
    db_path = get_db_path()
    if not db_path.exists():
        console.print("[yellow]⚠ 尚未导入数据，请先运行 citationer import[/yellow]")
        return []
    records = load_records_from_db(db_path)
    if not records:
        console.print("[yellow]⚠ 数据库中没有记录[/yellow]")
    return records


@app.command(name="overview")
def overview() -> None:
    """文献全景概览：总量、年份、作者、机构、引用等。"""
    records = _get_records()
    if not records:
        return

    engine = StatsEngine(records)
    stats = engine.overview()

    table = Table(
        title="📊 文献全景概览",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("指标", style="dim")
    table.add_column("数值", justify="right")

    table.add_row("总文献数", str(stats.total_records))
    year_range = (
        f"{stats.year_min} ~ {stats.year_max}" if stats.year_min else "-"
    )
    table.add_row("覆盖年份", year_range)
    table.add_row("来源/期刊数", str(stats.num_journals))
    table.add_row("作者总数", str(stats.num_authors))
    table.add_row("独著率", f"{stats.solo_rate:.1%}")
    table.add_row("合作率", f"{stats.coop_rate:.1%}")
    table.add_row("机构数", str(stats.num_institutions))
    table.add_row("涉及国家/地区数", str(stats.num_countries))
    table.add_row("平均引用次数", f"{stats.avg_citations:.1f}")
    table.add_row("h-index", str(stats.h_index))

    console.print(table)

    # Language distribution
    if stats.language_dist:
        console.print()
        lang_table = Table(title="语言分布", show_header=True, header_style="bold")
        lang_table.add_column("语言")
        lang_table.add_column("数量", justify="right")
        lang_table.add_column("占比", justify="right")
        for lang, count in stats.language_dist.items():
            pct = f"{count / stats.total_records * 100:.1f}%"
            lang_table.add_row(lang, str(count), pct)
        console.print(lang_table)

    # Doc type distribution
    if stats.doc_type_dist:
        console.print()
        dt_table = Table(title="文献类型分布", show_header=True, header_style="bold")
        dt_table.add_column("类型")
        dt_table.add_column("数量", justify="right")
        dt_table.add_column("占比", justify="right")
        for dtype, count in stats.doc_type_dist.items():
            pct = f"{count / stats.total_records * 100:.1f}%"
            dt_table.add_row(dtype, str(count), pct)
        console.print(dt_table)


# ── shared chart flags ─────────────────────────────────────────────


def _no_chart_flag() -> bool:
    """Return True if the --no-chart flag was passed on the command line."""
    return "--no-chart" in sys.argv


def _chart_only_flag() -> bool:
    """Return True if the --chart-only flag was passed on the command line."""
    return "--chart-only" in sys.argv


# ── yearly ──────────────────────────────────────────────────────────


@app.command(name="yearly")
def yearly(
    cumulative: bool = typer.Option(
        False, "--cumulative", "-c", help="显示累积发表量"
    ),
    no_chart: bool = typer.Option(
        False, "--no-chart", help="禁用终端图表，仅显示表格"
    ),
    chart_only: bool = typer.Option(
        False, "--chart-only", help="仅显示终端图表，不显示表格"
    ),
) -> None:
    """年度发表趋势分析。默认显示 braille 折线图。"""
    records = _get_records()
    if not records:
        return

    engine = StatsEngine(records)
    stats = engine.yearly()

    if not stats.year_counts:
        console.print("[yellow]没有可统计的年份数据[/yellow]")
        return

    years = sorted(stats.year_counts)
    counts = [stats.year_counts[y] for y in years]

    # ── Chart ──
    if not no_chart:
        if cumulative:
            cum_values = [stats.cumulative[y] for y in years]
            chart = plot_line_dual(years, counts, cum_values)
        else:
            chart = plot_line(years, counts)

        if chart:
            console.out(chart)
            if stats.trend_slope != 0:
                direction = "上升" if stats.trend_slope > 0 else "下降"
                console.print(
                    f"[dim]趋势: {direction} (斜率: {stats.trend_slope:.2f}/年) · "
                    f"总计: {sum(counts)} 篇[/dim]"
                )

    if chart_only:
        return

    # ── Table ──
    table = Table(
        title="📈 年度发表趋势",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("年份", justify="center")
    table.add_column("发表数量", justify="right")

    if cumulative:
        table.add_column("累积数量", justify="right")

    for year in sorted(stats.year_counts):
        count = stats.year_counts[year]
        if cumulative:
            table.add_row(str(year), str(count), str(stats.cumulative[year]))
        else:
            table.add_row(str(year), str(count))

    console.print(table)

    if stats.trend_slope != 0:
        direction = "上升" if stats.trend_slope > 0 else "下降"
        console.print(f"趋势: {direction} (斜率: {stats.trend_slope:.2f}/年)")


# ── journals ────────────────────────────────────────────────────────


@app.command(name="journals")
def journals(
    top: int = typer.Option(20, "--top", "-n", help="显示 Top-N 期刊"),
    no_chart: bool = typer.Option(
        False, "--no-chart", help="禁用终端图表，仅显示表格"
    ),
    chart_only: bool = typer.Option(
        False, "--chart-only", help="仅显示终端图表，不显示表格"
    ),
) -> None:
    """期刊/来源分析：Top-N 高产期刊。默认显示水平条形图。"""
    records = _get_records()
    if not records:
        return

    engine = StatsEngine(records)
    result = engine.journals(top_n=top)

    # ── Chart ──
    if not no_chart and result.items:
        labels = [name for name, _ in result.items]
        values = [count for _, count in result.items]
        chart = plot_hbar(labels, values, title=f"Top {min(top, len(labels))} Journals")
        if chart:
            console.out(chart)

    if chart_only:
        # Still show total count
        console.print(f"[dim]共 {result.total_unique} 个不同期刊/来源[/dim]")
        return

    # ── Table ──
    table = Table(
        title=f"📰 Top-{top} 高产期刊/来源",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("期刊/来源")
    table.add_column("发文量", justify="right")

    for i, (name, count) in enumerate(result.items, 1):
        table.add_row(str(i), name, str(count))

    console.print(table)
    console.print(f"共 {result.total_unique} 个不同期刊/来源")


# ── authors ─────────────────────────────────────────────────────────


@app.command(name="authors")
def authors(
    top: int = typer.Option(20, "--top", "-n", help="显示 Top-N 作者"),
    no_chart: bool = typer.Option(
        False, "--no-chart", help="禁用终端图表，仅显示表格"
    ),
    chart_only: bool = typer.Option(
        False, "--chart-only", help="仅显示终端图表，不显示表格"
    ),
) -> None:
    """作者分析：高产作者、独著率、合作率等。默认显示水平条形图。"""
    records = _get_records()
    if not records:
        return

    engine = StatsEngine(records)
    result = engine.authors(top_n=top)

    # ── Chart ──
    if not no_chart and result.top_authors.items:
        labels = [name for name, _ in result.top_authors.items]
        values = [count for _, count in result.top_authors.items]
        chart = plot_hbar(labels, values, title=f"Top {min(top, len(labels))} Authors")
        if chart:
            console.out(chart)

    if chart_only:
        # Still show key stats
        console.print(f"[dim]作者总数: {result.top_authors.total_unique} · "
                      f"独著: {result.solo_count} · 合著: {result.coop_count} · "
                      f"篇均作者: {result.avg_authors_per_paper:.1f}[/dim]")
        if result.core_authors:
            core_list = ", ".join(result.core_authors[:10])
            console.print(f"[bold]核心作者 (Price 定律)[/bold]: {core_list}")
        return

    # ── Table ──
    table = Table(
        title=f"👤 Top-{top} 高产作者",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("作者")
    table.add_column("发文量", justify="right")
    table.add_column("h-index", justify="right")

    author_h = dict(result.author_h_index)
    for i, (name, count) in enumerate(result.top_authors.items, 1):
        h = author_h.get(name, 0)
        table.add_row(str(i), name, str(count), str(h))

    console.print(table)

    # Author stats summary
    console.print()
    summary = Table(title="作者统计摘要", show_header=True, header_style="bold")
    summary.add_column("指标")
    summary.add_column("数值", justify="right")
    summary.add_row("作者总数", str(result.top_authors.total_unique))
    summary.add_row("独著篇数", str(result.solo_count))
    summary.add_row("合著篇数", str(result.coop_count))
    summary.add_row("篇均作者数", f"{result.avg_authors_per_paper:.1f}")
    console.print(summary)

    if result.core_authors:
        console.print()
        core_list = ", ".join(result.core_authors[:10])
        console.print(f"[bold]核心作者 (Price 定律)[/bold]: {core_list}")


# ── institutions ────────────────────────────────────────────────────


@app.command(name="institutions")
def institutions(
    top: int = typer.Option(20, "--top", "-n", help="显示 Top-N 机构"),
    no_chart: bool = typer.Option(
        False, "--no-chart", help="禁用终端图表，仅显示表格"
    ),
    chart_only: bool = typer.Option(
        False, "--chart-only", help="仅显示终端图表，不显示表格"
    ),
) -> None:
    """机构分析：Top-N 高产机构和分布。默认显示水平条形图。"""
    records = _get_records()
    if not records:
        return

    engine = StatsEngine(records)
    result = engine.institutions(top_n=top)

    # ── Chart ──
    if not no_chart and result.items:
        labels = [name for name, _ in result.items]
        values = [count for _, count in result.items]
        chart = plot_hbar(labels, values, title=f"Top {min(top, len(labels))} Institutions")
        if chart:
            console.out(chart)

    if chart_only:
        console.print(f"[dim]共 {result.total_unique} 个不同机构[/dim]")
        return

    # ── Table ──
    table = Table(
        title=f"🏛 Top-{top} 高产机构",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("机构")
    table.add_column("发文量", justify="right")

    for i, (name, count) in enumerate(result.items, 1):
        table.add_row(str(i), name, str(count))

    console.print(table)
    console.print(f"共 {result.total_unique} 个不同机构")
