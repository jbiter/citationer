"""Interactive wizard mode — guided step-by-step analysis."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from citationer.analysis.network import NetworkEngine
from citationer.analysis.stats import StatsEngine
from citationer.analysis.text import TextEngine
from citationer.analysis.trend import TrendEngine
from citationer.cli.scan_cmd import get_registry
from citationer.utils.config import get_db_path
from citationer.utils.db_loader import load_records_from_db

app = typer.Typer(
    name="interactive",
    help="交互式向导分析",
    invoke_without_command=True,
    no_args_is_help=False,
)

console = Console()


@app.callback()
def main(
    ctx: typer.Context,
) -> None:
    """Run an interactive guided analysis session."""
    if ctx.invoked_subcommand is not None:
        return
    _run_wizard()


def _run_wizard() -> None:
    """Main interactive loop."""
    console.print(
        Panel.fit(
            "🎓  Citationer Interactive Wizard\n"
            "引导式文献分析 — 选择步骤，逐步进行",
            border_style="cyan",
        )
    )
    console.print()

    # Step 1: Check data
    db_path = get_db_path()
    if not db_path.exists() or not list(db_path.glob("*")):
        console.print("[red]❌ 数据库为空，请先导入数据：[/red]")
        console.print("    [bold]ctr import[/bold] 或 [bold]ctr import <file>[/bold]")
        return

    records = load_records_from_db(db_path)
    if not records:
        console.print("[red]❌ 数据库中没有记录[/red]")
        return

    console.print(f"  [green]✓[/green] 已加载 [bold]{len(records)}[/bold] 条记录")
    console.print(f"  年份范围: {min(r.year for r in records if r.year)} – "
                  f"{max(r.year for r in records if r.year)}")
    console.print()

    # Step 2: Main menu loop
    while True:
        _print_menu()
        choice = Prompt.ask(
            "  选择操作",
            choices=["1", "2", "3", "4", "5", "6", "7", "q"],
            default="1",
        )
        console.print()

        if choice == "1":
            _interactive_stats(records)
        elif choice == "2":
            _interactive_text(records)
        elif choice == "3":
            _interactive_network(records)
        elif choice == "4":
            _interactive_trend(records)
        elif choice == "5":
            _interactive_scan()
        elif choice == "6":
            _interactive_export(records)
        elif choice == "7":
            _interactive_db()
        elif choice == "q":
            console.print("[cyan]👋 退出向导[/cyan]")
            return
        console.print()


def _print_menu() -> None:
    """Display the main menu."""
    table = Table(show_header=False, show_edge=False, box=None)
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()

    table.add_row("1", "📊 描述统计 (stats)")
    table.add_row("2", "🔤 文本分析 (text)")
    table.add_row("3", "🔗 网络分析 (network)")
    table.add_row("4", "📈 趋势分析 (trend)")
    table.add_row("5", "🔍 扫描目录 (scan)")
    table.add_row("6", "💾 导出数据 (export)")
    table.add_row("7", "🗃️  数据库管理")
    table.add_row("q", "🚪 退出")

    console.print(Panel(table, title="主菜单", border_style="blue"))


# ------------------------------------------------------------------
# Step handlers
# ------------------------------------------------------------------


def _interactive_stats(records) -> None:
    """Guided stats analysis."""
    console.print("[bold cyan]📊 描述统计[/bold cyan]")

    console.print("  [1] 概览仪表盘")
    console.print("  [2] 年度趋势（含图）")
    console.print("  [3] 高产期刊 Top-N")
    console.print("  [4] 高产作者 Top-N")
    console.print("  [5] 高产机构 Top-N")
    sub = Prompt.ask("  选择", choices=["1", "2", "3", "4", "5", "b"], default="1")

    if sub == "b":
        return

    engine = StatsEngine(records)

    if sub == "1":
        s = engine.overview()
        table = Table(title="📊 文献全景", show_header=False)
        table.add_column("指标", style="dim")
        table.add_column("值", justify="right")
        table.add_row("总文献数", str(s.total_records))
        y_min, y_max = s.year_min, s.year_max
        table.add_row("年份范围", f"{y_min}–{y_max}")
        table.add_row("作者总数", str(s.num_authors))
        table.add_row("机构总数", str(s.num_institutions))
        table.add_row("期刊数", str(s.num_journals))
        table.add_row("h-index", str(s.h_index))
        table.add_row("独著率", f"{s.solo_rate:.1%}")
        table.add_row("合作率", f"{s.coop_rate:.1%}")
        console.print(table)
    elif sub == "2":
        _show_yearly(engine)
    elif sub == "3":
        _show_top_journals(engine)
    elif sub == "4":
        _show_top_authors(engine)
    elif sub == "5":
        _show_top_institutions(engine)

    if Confirm.ask("  保存为报告？", default=False):
        Prompt.ask("  文件名", default="stats_report.md")
        console.print("  [dim]（保存功能待 report 命令完善）[/dim]")


def _interactive_text(records) -> None:
    """Guided text analysis."""
    console.print("[bold cyan]🔤 文本分析[/bold cyan]")
    console.print("  [1] 关键词频率 Top-N")
    console.print("  [2] 主题建模 (LDA/NMF)")
    console.print("  [3] 关键句摘要")
    choice = Prompt.ask("  选择", choices=["1", "2", "3", "b"], default="1")
    if choice == "b":
        return

    engine = TextEngine(records)
    if choice == "1":
        top = Prompt.ask("  Top-N 数量", default="20")
        result = engine.keywords(top_n=int(top))
        for i, (kw, cnt) in enumerate(result.top_keywords[:20], 1):
            console.print(f"  {i:2}. {kw:<20} {cnt:>5}")
    elif choice == "2":
        method = Prompt.ask("  方法", choices=["lda", "nmf"], default="lda")
        nt = Prompt.ask("  主题数", default="5")
        topics = engine.topics(num_topics=int(nt), method=method)
        for i, terms in enumerate(topics.topics, 1):
            ts = ", ".join(t for t, _ in terms[:5])
            console.print(f"  Topic {i}: {ts}")
    elif choice == "3":
        ms = Prompt.ask("  句子数", default="5")
        summary = engine.summarize(max_sentences=int(ms))
        for i, (sent, score) in enumerate(summary.sentences, 1):
            console.print(f"  {i}. ({score:.3f}) {sent[:120]}")


def _interactive_network(records) -> None:
    """Guided network analysis."""
    console.print("[bold cyan]🔗 网络分析[/bold cyan]")
    console.print("  [1] 关键词共现网络")
    console.print("  [2] 作者合作网络")
    console.print("  [3] 机构合作网络")
    choice = Prompt.ask("  选择", choices=["1", "2", "3", "b"], default="1")
    if choice == "b":
        return

    engine = NetworkEngine(records)
    if choice == "1":
        top = Prompt.ask("  Top-N 关键词", default="20")
        thr = Prompt.ask("  最低共现次数", default="3")
        result = engine.keyword_cooccurrence(top_n=int(top), threshold=int(thr))
        for i, (a, b, w) in enumerate(result.edges[:15], 1):
            console.print(f"  {i:2}. {a} ↔ {b}  ({w})")
    elif choice == "2":
        min_p = Prompt.ask("  最少发文数", default="2")
        collab = engine.author_collaboration(min_papers=int(min_p))
        console.print(f"  共 {collab.total_nodes} 位作者，{collab.total_edges} 条合作")
    elif choice == "3":
        min_p = Prompt.ask("  最少发文数", default="2")
        inst = engine.author_collaboration(
            min_papers=int(min_p), collab_type="institutions"
        )
        console.print(f"  共 {inst.total_nodes} 个机构，{inst.total_edges} 条合作")


def _interactive_trend(records) -> None:
    """Guided trend analysis."""
    console.print("[bold cyan]📈 趋势分析[/bold cyan]")
    console.print("  [1] 关键词突变检测")
    console.print("  [2] 战略坐标图")
    console.print("  [3] 主题河流图")
    choice = Prompt.ask("  选择", choices=["1", "2", "3", "b"], default="1")
    if choice == "b":
        return

    engine = TrendEngine(records)
    if choice == "1":
        hotspots = engine.hotspots(top_n=20)
        for i, b in enumerate(hotspots.bursts[:15], 1):
            console.print(f"  {i:2}. {b.keyword:<20} {b.start_year}–{b.end_year}  "
                          f"({b.strength:.1f}×)")
    elif choice == "2":
        strategy = engine.strategy(top_n=30)
        for i, t in enumerate(strategy.themes, 1):
            console.print(f"  {i}. {t.label}  C={t.centrality}  D={t.density}  Q{t.quadrant}")
    elif choice == "3":
        river = engine.river(top_n=8, window=5)
        for kw in river.keywords[:8]:
            console.print(f"  {kw}: {river.matrix.get(kw, [])}")
        console.print(f"  时间窗口: {river.windows}")


def _interactive_scan() -> None:
    """Scan a directory for bibliographic files."""
    console.print("[bold cyan]🔍 扫描目录[/bold cyan]")
    directory = Prompt.ask("  目录路径", default=".")
    p = Path(directory).resolve()
    if not p.exists():
        console.print(f"  [red]❌ 目录不存在: {p}[/red]")
        return

    registry = get_registry()
    found: list[tuple[Path, str]] = []
    supported_exts = {".xlsx", ".xls", ".txt", ".ciw", ".csv", ".xml", ".nbib", ".bib", ".ris"}
    for ext in supported_exts:
        for f in p.glob(f"*{ext}"):
            parser = registry.find_parser(f)
            if parser:
                found.append((f, parser.source_name))

    if not found:
        console.print("  [yellow]未找到受支持的题录文件[/yellow]")
        return

    table = Table(title=f"📁 扫描结果: {p}")
    table.add_column("文件", style="dim")
    table.add_column("来源")
    for f, src in found:
        table.add_row(f.name, src)
    console.print(table)


def _interactive_export(records) -> None:
    """Export to file."""
    import csv as csv_mod
    import json

    from citationer.utils.serialization import record_to_db_serializable

    console.print("[bold cyan]💾 导出数据[/bold cyan]")
    console.print("  [1] CSV")
    console.print("  [2] JSON")
    console.print("  [3] BibTeX")
    choice = Prompt.ask("  选择格式", choices=["1", "2", "3", "b"], default="1")
    if choice == "b":
        return

    fmt = {"1": "csv", "2": "json", "3": "bibtex"}[choice]

    out = Path.cwd() / "output" / "cls"
    out.mkdir(parents=True, exist_ok=True)
    name_map = {
        "csv": "cleaned_records.csv",
        "json": "cleaned_records.json",
        "bibtex": "cleaned_records.bib",
    }
    fname = Prompt.ask("  文件名", default=name_map[fmt])
    fpath = out / fname

    if fmt == "csv":
        with open(fpath, "w", newline="", encoding="utf-8-sig") as f:
            w = csv_mod.writer(f)
            w.writerow(["title", "authors", "year", "journal", "doi", "keywords"])
            for r in records:
                d = record_to_db_serializable(r)
                w.writerow([d["record_data"]["title"],
                           "; ".join(a["full_name"] for a in d["authors"]),
                           d["record_data"]["year"] or "",
                           d["record_data"]["journal"] or "",
                           d["record_data"]["doi"] or "",
                           "; ".join(k["keyword"] for k in d["keywords"])])
    elif fmt == "json":
        data = []
        for r in records:
            d = record_to_db_serializable(r)
            data.append({
                "title": d["record_data"]["title"],
                "authors": [a["full_name"] for a in d["authors"]],
                "year": d["record_data"]["year"],
                "journal": d["record_data"]["journal"],
                "doi": d["record_data"]["doi"],
                "keywords": [k["keyword"] for k in d["keywords"]],
            })
        fpath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    elif fmt == "bibtex":
        lines = []
        for i, r in enumerate(records):
            key = f"ref{i+1}"
            lines.append(f"@article{{{key},")
            lines.append(f"  title = {{{r.title}}},")
            if r.authors:
                lines.append("  author = {" +
                             " and ".join(a.full_name for a in r.authors) + "},")
            if r.year:
                lines.append(f"  year = {{{r.year}}},")
            if r.journal:
                lines.append(f"  journal = {{{r.journal}}},")
            if r.doi:
                lines.append(f"  doi = {{{r.doi}}},")
            lines.append("}")
            lines.append("")
        fpath.write_text("\n".join(lines), encoding="utf-8")

    console.print(f"  [green]✓ 已导出: {fpath}[/green]")


def _interactive_db() -> None:
    """Database management."""
    console.print("[bold cyan]🗃️ 数据库管理[/bold cyan]")
    db_path = get_db_path()
    if not db_path.exists():
        console.print("  [yellow]数据库文件不存在[/yellow]")
        return

    size_mb = db_path.stat().st_size / 1024 / 1024

    table = Table(title="数据库信息", show_header=False)
    table.add_column(style="dim")
    table.add_column()
    table.add_row("路径", str(db_path))
    table.add_row("大小", f"{size_mb:.1f} MB")
    console.print(table)
    console.print()

    if Confirm.ask("  清理数据库（清空所有记录）？", default=False):
        from citationer.utils.database import CitationDatabase
        db = CitationDatabase(db_path)
        db.clear_records()
        console.print("  [green]✓ 数据库已清空[/green]")


# ── helpers ────────────────────────────────────────────────────────


def _show_yearly(engine: StatsEngine) -> None:
    from citationer.viz.terminal_charts import plot_line
    result = engine.yearly()
    if not result.year_counts:
        console.print("  [yellow]没有可统计的年份数据[/yellow]")
        return
    years = sorted(result.year_counts)
    counts = [result.year_counts[y] for y in years]
    if plot_line(years, counts):
        console.print(f"  [dim]趋势: 斜率 {result.trend_slope:.2f}/年[/dim]")


def _show_top_journals(engine: StatsEngine) -> None:
    from citationer.viz.terminal_charts import plot_hbar
    n = int(Prompt.ask("  Top-N", default="20"))
    result = engine.journals(top_n=n)
    if result.items:
        plot_hbar(
            [name for name, _ in result.items],
            [cnt for _, cnt in result.items],
            title=f"Top {len(result.items)} Journals",
        )


def _show_top_authors(engine: StatsEngine) -> None:
    from citationer.viz.terminal_charts import plot_hbar
    n = int(Prompt.ask("  Top-N", default="20"))
    result = engine.authors(top_n=n)
    if result.top_authors.items:
        plot_hbar(
            [name for name, _ in result.top_authors.items],
            [cnt for _, cnt in result.top_authors.items],
            title=f"Top {len(result.top_authors.items)} Authors",
        )


def _show_top_institutions(engine: StatsEngine) -> None:
    from citationer.viz.terminal_charts import plot_hbar
    n = int(Prompt.ask("  Top-N", default="20"))
    result = engine.institutions(top_n=n)
    if result.items:
        plot_hbar(
            [name for name, _ in result.items],
            [cnt for _, cnt in result.items],
            title=f"Top {len(result.items)} Institutions",
        )


if __name__ == "__main__":
    app()
