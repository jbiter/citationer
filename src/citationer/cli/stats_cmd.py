"""Stats commands — descriptive statistical analysis."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from citationer.analysis.stats import StatsEngine
from citationer.utils.config import get_db_path
from citationer.utils.db_loader import load_records_from_db
from citationer.viz.charts import generate_top_n_chart, generate_yearly_chart
from citationer.viz.terminal_charts import plot_hbar, plot_line, plot_line_dual

app = typer.Typer(
    name="stats",
    help="描述性统计分析",
    no_args_is_help=True,
)

console = Console()


def _resolve_png(path: Path | None, default_name: str) -> Path:
    """Resolve PNG output path. Defaults to output/viz/<name>."""
    if path:
        return path
    out = Path.cwd() / "output" / "viz"
    out.mkdir(parents=True, exist_ok=True)
    return out / default_name


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


# ── yearly ──────────────────────────────────────────────────────────


@app.command(name="yearly")
def yearly(
    cumulative: bool = typer.Option(
        False, "--cumulative", "-c", help="显示累积发表量"
    ),
    table: bool = typer.Option(
        False, "--table", "-t", help="同时显示数据表格"
    ),
    save_img: Path | None = typer.Option(
        None, "--save", help="保存为 PNG/SVG 图片（默认 output/viz/）"
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

    # ── PNG export ──
    if save_img:
        out = _resolve_png(save_img, "yearly_trend.png")
        generate_yearly_chart(records, out, cumulative=cumulative)
        console.print(f"[green]📈 PNG 已保存: {out}[/green]")

    # ── Chart (always, if TTY) ──
    if cumulative:
        cum_values = [stats.cumulative[y] for y in years]
        chart_ok = plot_line_dual(years, counts, cum_values)
    else:
        chart_ok = plot_line(years, counts)

    if chart_ok and stats.trend_slope != 0:
        direction = "上升" if stats.trend_slope > 0 else "下降"
        console.print(
            f"[dim]趋势: {direction} (斜率: {stats.trend_slope:.2f}/年) · "
            f"总计: {sum(counts)} 篇[/dim]"
        )

    # ── Table (only if --table) ──
    if not table:
        return

    tbl = Table(
        title="📈 年度发表趋势",
        show_header=True,
        header_style="bold cyan",
    )
    tbl.add_column("年份", justify="center")
    tbl.add_column("发表数量", justify="right")

    if cumulative:
        tbl.add_column("累积数量", justify="right")

    for year in sorted(stats.year_counts):
        count = stats.year_counts[year]
        if cumulative:
            tbl.add_row(str(year), str(count), str(stats.cumulative[year]))
        else:
            tbl.add_row(str(year), str(count))

    console.print(tbl)

    if stats.trend_slope != 0:
        direction = "上升" if stats.trend_slope > 0 else "下降"
        console.print(f"趋势: {direction} (斜率: {stats.trend_slope:.2f}/年)")


# ── journals ────────────────────────────────────────────────────────


@app.command(name="journals")
def journals(
    top: int = typer.Option(20, "--top", "-n", help="显示 Top-N 期刊"),
    table: bool = typer.Option(
        False, "--table", "-t", help="同时显示数据表格"
    ),
    save_img: Path | None = typer.Option(
        None, "--save", help="保存为 PNG/SVG 图片（默认 output/viz/）"
    ),
) -> None:
    """期刊/来源分析：Top-N 高产期刊。默认显示水平条形图。"""
    records = _get_records()
    if not records:
        return

    engine = StatsEngine(records)
    result = engine.journals(top_n=top)

    # ── Chart ──
    if result.items:
        labels = [name for name, _ in result.items]
        values = [count for _, count in result.items]
        plot_hbar(labels, values, title=f"Top {min(top, len(labels))} Journals")

    if save_img:
        out = _resolve_png(save_img, "top_journals.png")
        generate_top_n_chart(
            result.items, out, title=f"Top {min(top, len(result.items))} Journals",
            xlabel="Publications",
        )
        console.print(f"[green]📰 PNG 已保存: {out}[/green]")

    console.print(f"[dim]共 {result.total_unique} 个不同期刊/来源[/dim]")

    if not table:
        return

    # ── Table ──
    tbl = Table(
        title=f"📰 Top-{top} 高产期刊/来源",
        show_header=True,
        header_style="bold cyan",
    )
    tbl.add_column("#", justify="right", style="dim")
    tbl.add_column("期刊/来源")
    tbl.add_column("发文量", justify="right")

    for i, (name, count) in enumerate(result.items, 1):
        tbl.add_row(str(i), name, str(count))

    console.print(tbl)
    console.print(f"共 {result.total_unique} 个不同期刊/来源")


# ── authors ─────────────────────────────────────────────────────────


@app.command(name="authors")
def authors(
    top: int = typer.Option(20, "--top", "-n", help="显示 Top-N 作者"),
    table: bool = typer.Option(
        False, "--table", "-t", help="同时显示数据表格"
    ),
    save_img: Path | None = typer.Option(
        None, "--save", help="保存为 PNG/SVG 图片（默认 output/viz/）"
    ),
) -> None:
    """作者分析：高产作者、独著率、合作率等。默认显示水平条形图。"""
    records = _get_records()
    if not records:
        return

    engine = StatsEngine(records)
    result = engine.authors(top_n=top)

    # ── Chart ──
    if result.top_authors.items:
        labels = [name for name, _ in result.top_authors.items]
        values = [count for _, count in result.top_authors.items]
        plot_hbar(labels, values, title=f"Top {min(top, len(labels))} Authors")

    if save_img:
        out = _resolve_png(save_img, "top_authors.png")
        generate_top_n_chart(
            result.top_authors.items, out,
            title=f"Top {min(top, len(result.top_authors.items))} Authors",
            xlabel="Publications",
        )
        console.print(f"[green]👤 PNG 已保存: {out}[/green]")

    # ── Always show key stats ──
    console.print(f"[dim]作者总数: {result.top_authors.total_unique} · "
                  f"独著: {result.solo_count} · 合著: {result.coop_count} · "
                  f"篇均作者: {result.avg_authors_per_paper:.1f}[/dim]")
    if result.core_authors:
        core_list = ", ".join(result.core_authors[:10])
        console.print(f"[bold]核心作者 (Price 定律)[/bold]: {core_list}")

    if not table:
        return

    # ── Table ──
    tbl = Table(
        title=f"👤 Top-{top} 高产作者",
        show_header=True,
        header_style="bold cyan",
    )
    tbl.add_column("#", justify="right", style="dim")
    tbl.add_column("作者")
    tbl.add_column("发文量", justify="right")
    tbl.add_column("h-index", justify="right")

    author_h = dict(result.author_h_index)
    for i, (name, count) in enumerate(result.top_authors.items, 1):
        h = author_h.get(name, 0)
        tbl.add_row(str(i), name, str(count), str(h))

    console.print(tbl)

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
    table: bool = typer.Option(
        False, "--table", "-t", help="同时显示数据表格"
    ),
    save_img: Path | None = typer.Option(
        None, "--save", help="保存为 PNG/SVG 图片（默认 output/viz/）"
    ),
) -> None:
    """机构分析：Top-N 高产机构和分布。默认显示水平条形图。"""
    records = _get_records()
    if not records:
        return

    engine = StatsEngine(records)
    result = engine.institutions(top_n=top)

    # ── Chart ──
    if result.items:
        labels = [name for name, _ in result.items]
        values = [count for _, count in result.items]
        plot_hbar(labels, values, title=f"Top {min(top, len(labels))} Institutions")

    if save_img:
        out = _resolve_png(save_img, "top_institutions.png")
        generate_top_n_chart(
            result.items, out, title=f"Top {min(top, len(result.items))} Institutions",
            xlabel="Publications",
        )
        console.print(f"[green]🏛 PNG 已保存: {out}[/green]")

    console.print(f"[dim]共 {result.total_unique} 个不同机构[/dim]")

    if not table:
        return

    # ── Table ──
    tbl = Table(
        title=f"🏛 Top-{top} 高产机构",
        show_header=True,
        header_style="bold cyan",
    )
    tbl.add_column("#", justify="right", style="dim")
    tbl.add_column("机构")
    tbl.add_column("发文量", justify="right")

    for i, (name, count) in enumerate(result.items, 1):
        tbl.add_row(str(i), name, str(count))

    console.print(tbl)
    console.print(f"共 {result.total_unique} 个不同机构")


# ── citations ─────────────────────────────────────────────────────


@app.command(name="citations")
def citations(
    top_n: int = typer.Option(20, "--top", "-n", help="显示 Top-N 高被引论文"),
) -> None:
    """引用分析：高被引论文排名、引用分布统计。"""
    records = _get_records()
    if not records:
        return

    # Top cited papers
    cited = [(r, r.citation_count or 0) for r in records if r.citation_count]
    cited.sort(key=lambda x: -x[1])
    top = cited[:top_n]

    table = Table(
        title=f"📖 Top-{min(top_n, len(top))} 高被引论文",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("标题")
    table.add_column("引用数", justify="right")
    table.add_column("年份", justify="center")

    for i, (r, cnt) in enumerate(top, 1):
        title = r.title[:60] + "…" if len(r.title) > 60 else r.title
        table.add_row(str(i), title, str(cnt), str(r.year or "-"))

    console.print(table)

    # Citation distribution
    if cited:
        counts = [c for _, c in cited]
        avg = sum(counts) / len(counts)
        median = sorted(counts)[len(counts) // 2]
        console.print()
        console.print(
            f"[dim]引用分布: 均值 {avg:.1f} · 中位数 {median} · "
            f"范围 {min(counts)}–{max(counts)} · "
            f"总被引 {sum(counts)}[/dim]"
        )


# ── funding ──────────────────────────────────────────────────────


@app.command(name="funding")
def funding(
    top_n: int = typer.Option(20, "--top", "-n", help="显示 Top-N 基金来源"),
) -> None:
    """基金资助分析（F-2.6）：资助率、Top-N 基金来源、年度趋势。"""
    records = _get_records()
    if not records:
        return

    engine = StatsEngine(records)
    stats = engine.funding(top_n=top_n)

    # Overview table: funded / unfunded / rate
    console.print()
    overview = Table(
        title="💰 基金资助概览",
        show_header=True,
        header_style="bold cyan",
    )
    overview.add_column("指标")
    overview.add_column("数量", justify="right")
    overview.add_column("占比", justify="right")
    total = stats.funded_count + stats.unfunded_count
    overview.add_row(
        "有基金标注",
        str(stats.funded_count),
        f"{stats.funded_count / total * 100:.1f}%" if total else "-",
    )
    overview.add_row(
        "无基金标注",
        str(stats.unfunded_count),
        f"{stats.unfunded_count / total * 100:.1f}%" if total else "-",
    )
    overview.add_row(
        "[bold]资助率[/bold]",
        "[bold green]"
        + f"{stats.funding_rate * 100:.1f}%"
        + "[/bold green]",
        "",
    )
    console.print(overview)

    # Top funders
    if stats.top_funders.items:
        console.print()
        funder_table = Table(
            title=f"🏛️  Top-{min(top_n, len(stats.top_funders.items))} 基金来源",
            show_header=True,
            header_style="bold cyan",
        )
        funder_table.add_column("#", justify="right", style="dim")
        funder_table.add_column("基金名称")
        funder_table.add_column("资助论文数", justify="right")

        for i, (name, cnt) in enumerate(stats.top_funders.items, 1):
            funder_table.add_row(str(i), name, str(cnt))
        console.print(funder_table)
        console.print(
            f"[dim]共 {stats.top_funders.total_unique} 个独立基金来源[/dim]"
        )
    else:
        console.print("[dim]无基金来源数据[/dim]")

    # Yearly funding trend (mini-bar chart in rich)
    if stats.yearly_funded:
        console.print()
        trend_table = Table(
            title="📅 年度资助趋势",
            show_header=True,
            header_style="bold cyan",
        )
        trend_table.add_column("年份", justify="center")
        trend_table.add_column("资助论文数", justify="right")
        trend_table.add_column("占比", justify="right")
        max_v = max(stats.yearly_funded.values())
        for y in sorted(stats.yearly_funded):
            v = stats.yearly_funded[y]
            bar = "█" * int(v / max_v * 20) if max_v else ""
            trend_table.add_row(str(y), str(v), bar)
        console.print(trend_table)
