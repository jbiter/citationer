"""Declarative pipeline runner — execute a YAML config of analysis steps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console

from citationer.analysis.network import NetworkEngine
from citationer.analysis.stats import StatsEngine
from citationer.analysis.text import TextEngine
from citationer.analysis.trend import TrendEngine
from citationer.utils.config import get_db_path
from citationer.utils.db_loader import load_records_from_db

app = typer.Typer(
    name="run",
    help="执行声明式分析流水线（YAML 配置文件）",
    invoke_without_command=True,
    no_args_is_help=False,
)

console = Console()


@app.callback()
def main(
    ctx: typer.Context,
    config_file: Path = typer.Argument(
        ..., help="YAML 配置文件路径",
    ),
    output_dir: Path = typer.Option(
        None, "--output", "-o", help="输出目录（覆盖配置文件中的设置）"
    ),
) -> None:
    """Execute a YAML pipeline file."""
    if not config_file.exists():
        console.print(f"[red]❌ 配置文件不存在: {config_file}[/red]")
        raise typer.Exit(1)

    try:
        config = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        console.print(f"[red]❌ YAML 解析失败: {e}[/red]")
        raise typer.Exit(1)

    if not config:
        console.print("[red]❌ 配置文件为空[/red]")
        raise typer.Exit(1)

    _run_pipeline(config, config_file, output_dir)


def _run_pipeline(
    config: dict[str, Any],
    config_file: Path,
    output_override: Path | None,
) -> None:
    """Execute the pipeline defined by *config*."""
    # Load records
    db_path = get_db_path()
    if not db_path.exists():
        console.print("[red]❌ 数据库为空，请先运行 citationer import[/red]")
        raise typer.Exit(1)

    records = load_records_from_db(db_path)
    if not records:
        console.print("[red]❌ 数据库中没有记录[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]📊 加载 {len(records)} 条记录[/bold]")

    # Determine output directory
    out_dir = output_override or Path(config.get("output_dir", "output/analysis"))
    out_dir.mkdir(parents=True, exist_ok=True)

    # Pipeline name from config
    pipeline_name = config.get("name", config_file.stem)
    console.print(f"[bold cyan]▶ 流水线: {pipeline_name}[/bold cyan]")
    console.print()

    # Execute steps
    steps = config.get("steps", [])
    if not steps:
        console.print("[red]❌ 配置文件中未定义 steps[/red]")
        raise typer.Exit(1)

    results: dict[str, Any] = {}
    for i, step in enumerate(steps, 1):
        action = step.get("action")
        name = step.get("name", action or f"step{i}")
        if not action:
            console.print(f"  [yellow]步骤 {i}: 缺少 action，跳过[/yellow]")
            continue

        console.print(f"  [bold cyan]步骤 {i}/{len(steps)}: {name}[/bold cyan]")

        try:
            output = _execute_step(action, step, records, results, out_dir)
            if name:
                results[name] = output
            console.print("    [green]✓ 完成[/green]")
        except Exception as e:
            console.print(f"    [red]✗ 失败: {e}[/red]")
            # BUG-010 fix: mark the step as None in results so subsequent
            # steps that reference it via `name` get a clear signal (None)
            # rather than a confusing KeyError from a stale reference.
            if name:
                results[name] = None
                console.print(
                    f"    [dim]步骤 '{name}' 输出未生成，后续引用将得到 None[/dim]"
                )
            if step.get("on_error") == "stop":
                raise typer.Exit(1)
        console.print()

    # Summary
    console.print(f"[bold green]✓ 流水线完成，结果保存到 {out_dir}[/bold green]")


def _execute_step(
    action: str,
    step: dict[str, Any],
    records: list,
    results: dict[str, Any],
    out_dir: Path,
) -> Any:
    """Dispatch a single step to its handler."""
    handlers = {
        "stats": _run_stats_step,
        "text": _run_text_step,
        "network": _run_network_step,
        "trend": _run_trend_step,
        "export": _run_export_step,
    }
    handler = handlers.get(action)
    if handler is None:
        raise ValueError(f"未知 action: {action}")
    return handler(step, records, results, out_dir)


def _run_stats_step(
    step: dict[str, Any],
    records: list,
    results: dict[str, Any],
    out_dir: Path,
) -> Any:
    """Run a stats analysis step."""
    engine = StatsEngine(records)
    stat_type = step.get("type", "overview")
    output_name = step.get("output", f"stats_{stat_type}.txt")

    if stat_type == "overview":
        overview = engine.overview()
        _save_stats_overview(overview, out_dir / output_name)
        return overview
    if stat_type == "yearly":
        yearly = engine.yearly()
        _save_yearly(yearly, out_dir / output_name)
        return yearly
    if stat_type == "journals":
        n = step.get("top", 20)
        journals = engine.journals(top_n=n)
        _save_top_list(journals, out_dir / output_name, "Journal")
        return journals
    if stat_type == "authors":
        n = step.get("top", 20)
        authors = engine.authors(top_n=n)
        _save_top_list(authors, out_dir / output_name, "Author", authors.top_authors)
        return authors
    if stat_type == "institutions":
        n = step.get("top", 20)
        institutions = engine.institutions(top_n=n)
        _save_top_list(institutions, out_dir / output_name, "Institution")
        return institutions
    raise ValueError(f"未知 stats type: {stat_type}")


def _run_text_step(
    step: dict[str, Any],
    records: list,
    results: dict[str, Any],
    out_dir: Path,
) -> Any:
    """Run a text analysis step."""
    engine = TextEngine(records)
    text_type = step.get("type", "keywords")
    output_name = step.get("output", f"text_{text_type}.txt")

    if text_type == "keywords":
        n = step.get("top", 30)
        kw_result = engine.keywords(top_n=n, per_year=step.get("per_year", False))
        _save_keywords(kw_result, out_dir / output_name)
        return kw_result
    if text_type == "topics":
        nt = step.get("num_topics", 5)
        method = step.get("method", "lda")
        topic_result = engine.topics(num_topics=nt, method=method)
        _save_topics(topic_result, out_dir / output_name)
        return topic_result
    if text_type == "summarize":
        ms = step.get("max_sentences", 5)
        summary = engine.summarize(max_sentences=ms)
        _save_summarize(summary, out_dir / output_name)
        return summary
    raise ValueError(f"未知 text type: {text_type}")


def _run_network_step(
    step: dict[str, Any],
    records: list,
    results: dict[str, Any],
    out_dir: Path,
) -> Any:
    """Run a network analysis step."""
    engine = NetworkEngine(records)
    net_type = step.get("type", "keywords")
    output_name = step.get("output", f"network_{net_type}.csv")

    if net_type == "keywords":
        n = step.get("top", 20)
        thr = step.get("threshold", 3)
        result = engine.keyword_cooccurrence(top_n=n, threshold=thr)
        _save_network_edges(result, out_dir / output_name)
        return result
    if net_type in ("coauthors", "institutions"):
        min_p = step.get("min_papers", 2)
        ct = "institutions" if net_type == "institutions" else "authors"
        collab = engine.author_collaboration(min_papers=min_p, collab_type=ct)
        _save_network_edges(collab, out_dir / output_name)
        return collab
    raise ValueError(f"未知 network type: {net_type}")


def _run_trend_step(
    step: dict[str, Any],
    records: list,
    results: dict[str, Any],
    out_dir: Path,
) -> Any:
    """Run a trend analysis step."""
    engine = TrendEngine(records)
    trend_type = step.get("type", "hotspots")
    output_name = step.get("output", f"trend_{trend_type}.txt")

    if trend_type == "hotspots":
        n = step.get("top", 30)
        hotspots_result = engine.hotspots(top_n=n)
        _save_hotspots(hotspots_result, out_dir / output_name)
        return hotspots_result
    if trend_type == "strategy":
        n = step.get("top", 50)
        strategy = engine.strategy(top_n=n)
        _save_strategy(strategy, out_dir / output_name)
        return strategy
    raise ValueError(f"未知 trend type: {trend_type}")


def _run_export_step(
    step: dict[str, Any],
    records: list,
    results: dict[str, Any],
    out_dir: Path,
) -> Any:
    """Run an export step."""
    fmt = step.get("format", "csv")
    output_name = step.get("output", f"output.{fmt}")
    fpath = out_dir / output_name

    import csv as csv_mod
    import json

    from citationer.utils.serialization import record_to_db_serializable

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
    else:
        raise ValueError(f"未知 export format: {fmt}")

    return str(fpath)


# ── save helpers ──────────────────────────────────────────────────


def _save_stats_overview(result, path: Path) -> None:
    lines = [
        "Citationer Statistics Overview",
        "=" * 40,
        f"Total records: {result.total_records}",
        f"Year range:   {result.year_min}–{result.year_max}",
        f"Unique authors: {result.num_authors}",
        f"Unique institutions: {result.num_institutions}",
        f"Unique journals: {result.num_journals}",
        f"Solo rate:   {result.solo_rate:.1%}",
        f"Coop rate:   {result.coop_rate:.1%}",
        f"h-index:     {result.h_index}",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _save_yearly(result, path: Path) -> None:
    lines = ["Year,Publications,Cumulative"]
    cum = 0
    for y in sorted(result.year_counts):
        cum += result.year_counts[y]
        lines.append(f"{y},{result.year_counts[y]},{cum}")
    path.write_text("\n".join(lines), encoding="utf-8")


def _save_top_list(result, path: Path, kind: str, top_list=None) -> None:
    items = top_list.items if top_list is not None else result.items
    lines = [f"Rank,{kind},Count"]
    for i, (name, cnt) in enumerate(items, 1):
        safe = name.replace('"', '""')
        lines.append(f'{i},"{safe}",{cnt}')
    path.write_text("\n".join(lines), encoding="utf-8")


def _save_keywords(result, path: Path) -> None:
    lines = ["Rank,Keyword,Frequency"]
    for i, (kw, cnt) in enumerate(result.top_keywords, 1):
        lines.append(f'{i},"{kw}",{cnt}')
    path.write_text("\n".join(lines), encoding="utf-8")


def _save_topics(result, path: Path) -> None:
    lines = [f"Topic Modeling (LDA, coherence={result.coherence_score:.3f})"]
    for i, terms in enumerate(result.topics, 1):
        ts = "; ".join(f"{t}:{w:.3f}" for t, w in terms)
        lines.append(f"Topic {i}: {ts}")
    path.write_text("\n".join(lines), encoding="utf-8")


def _save_summarize(result, path: Path) -> None:
    lines = ["Citationer Summarization (extractive)"]
    for i, (sent, score) in enumerate(result.sentences, 1):
        lines.append(f"\n[{i}] (score {score:.3f})\n{sent}")
    path.write_text("\n".join(lines), encoding="utf-8")


def _save_network_edges(result, path: Path) -> None:
    lines = ["Source,Target,Weight"]
    for a, b, w in result.edges:
        sa, sb = a.replace('"', '""'), b.replace('"', '""')
        lines.append(f'"{sa}","{sb}",{w}')
    path.write_text("\n".join(lines), encoding="utf-8")


def _save_hotspots(result, path: Path) -> None:
    lines = ["Keyword,Start,End,Strength"]
    for b in result.bursts:
        lines.append(f'"{b.keyword}",{b.start_year},{b.end_year},{b.strength}')
    path.write_text("\n".join(lines), encoding="utf-8")


def _save_strategy(result, path: Path) -> None:
    lines = ["Theme,Keywords,Centrality,Density,Quadrant"]
    quad_names = {1: "Motor", 2: "Niche", 3: "Emerging", 4: "Basic"}
    for t in result.themes:
        kw = ";".join(t.keywords)
        lines.append(f'"{t.label}","{kw}",{t.centrality},{t.density},'
                    f'"{quad_names.get(t.quadrant, t.quadrant)}"')
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    app()
