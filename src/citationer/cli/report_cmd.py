"""Report generation commands — one-click Markdown/HTML reports."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from citationer.analysis.network import NetworkEngine
from citationer.analysis.stats import StatsEngine
from citationer.analysis.text import TextEngine
from citationer.utils.db_loader import get_records

app = typer.Typer(
    name="report",
    help="报告生成",
    no_args_is_help=True,
)

console = Console()

_get_records = get_records

_VALID_TEMPLATES = ("academic", "simple")


# ---------------------------------------------------------------------------
# Template builders
# ---------------------------------------------------------------------------


def _overview_table(overview) -> list[str]:
    """Shared overview block (academic + simple)."""
    return [
        "## Overview\n",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total records | {overview.total_records} |",
        f"| Unique authors | {overview.num_authors} |",
        f"| Journals | {overview.num_journals} |",
        f"| Institutions | {overview.num_institutions} |",
        f"| Solo rate | {overview.solo_rate:.1%} |",
        f"| Avg citations | {overview.avg_citations:.1f} |",
        f"| h-index | {overview.h_index} |\n",
    ]


def _yearly_table(yearly, years: int = 10) -> list[str]:
    if not yearly.year_counts:
        return []
    out = ["## Publication Trend\n", "| Year | Publications |", "|------|-------------|"]
    for y in sorted(yearly.year_counts)[-years:]:
        out.append(f"| {y} | {yearly.year_counts[y]} |")
    out.append("")
    return out


def _top_table(
    title: str,
    items: list[tuple],
    columns: list[str] | None = None,
) -> list[str]:
    """Generic ranked list table.

    `items` is a list of tuples.  The default 2-tuple `(name, count)` maps to
    `["#", "Name", "Count"]`.  For N-column tables, pass `items` as N-tuples
    matching the supplied `columns` list.
    """
    if not items:
        return []
    columns = columns or ["#", "Name", "Count"]
    sep = ["---"] * len(columns)
    out = [f"## {title}\n", "| " + " | ".join(columns) + " |", "|" + "|".join(sep) + "|"]
    for i, row in enumerate(items, 1):
        # First column is always the rank; the rest are the row values.
        cells = (str(i),) + tuple(str(v) for v in row)
        # Truncate or pad to column count.
        cells = cells[: len(columns)]
        if len(cells) < len(columns):
            cells = cells + ("",) * (len(columns) - len(cells))
        out.append("| " + " | ".join(cells) + " |")
    out.append("")
    return out


def _build_academic(records) -> str:
    """Comprehensive academic-style report with all engines."""
    engine = StatsEngine(records)
    overview = engine.overview()
    yearly = engine.yearly()
    top_journals = engine.journals(top_n=10)
    top_authors = engine.authors(top_n=10)

    text = TextEngine(records)
    kw_result = text.keywords(top_n=10)
    topic_result = text.topics(num_topics=5, method="lda")

    net = NetworkEngine(records)
    cooc = net.keyword_cooccurrence(top_n=20, threshold=2)

    sections: list[str] = [
        "# Citationer Analysis Report\n",
        f"**Total records**: {overview.total_records}  ·  "
        f"**Year range**: {overview.year_min}–{overview.year_max}  ·  "
        f"**h-index**: {overview.h_index}\n",
    ]
    sections += _overview_table(overview)
    sections += _yearly_table(yearly, years=10)
    sections += _top_table("Top Journals", top_journals.items)

    # Top authors (with h-index column)
    if top_authors.top_authors.items:
        sections += [
            "## Top Authors\n",
            "| # | Author | Papers | h-index |",
            "|---|--------|--------|---------|",
        ]
        h_dict = dict(top_authors.author_h_index)
        for i, (name, count) in enumerate(top_authors.top_authors.items, 1):
            h = h_dict.get(name, 0)
            sections.append(f"| {i} | {name} | {count} | {h} |")
        sections.append("")

    sections += _top_table("Top Keywords", kw_result.top_keywords[:10])

    if topic_result.topics:
        sections += ["## Topic Modeling (LDA)\n"]
        if topic_result.coherence_score:
            sections.append(f"Coherence: {topic_result.coherence_score:.3f}\n")
        for i, terms in enumerate(topic_result.topics):
            term_str = ", ".join(t for t, _ in terms[:5])
            sections.append(f"- **Topic {i+1}**: {term_str}")
        sections.append("")

    if cooc.edges:
        sections += ["## Keyword Co-occurrence Network\n"]
        sections.append(f"Nodes: {cooc.total_keywords}  ·  Edges: {cooc.total_edges}\n")
        sections += [
            "| Keyword A | Keyword B | Weight |",
            "|-----------|-----------|--------|",
        ]
        for a, b, w in cooc.edges[:10]:
            sections.append(f"| {a} | {b} | {w} |")
        sections.append("")

    sections.append("\n---\n*Generated by Citationer · academic template*\n")
    return "\n".join(sections)


def _build_simple(records) -> str:
    """Concise report with only the essentials (stats + top-5 each)."""
    engine = StatsEngine(records)
    overview = engine.overview()
    yearly = engine.yearly()
    top_authors = engine.authors(top_n=5)

    text = TextEngine(records)
    kw_result = text.keywords(top_n=5)

    sections: list[str] = [
        "# Quick Summary\n",
        f"{overview.total_records} records · "
        f"years {overview.year_min}–{overview.year_max} · "
        f"h-index {overview.h_index}.\n",
    ]
    sections += _overview_table(overview)
    if yearly.year_counts:
        sections += _yearly_table(yearly, years=5)
    sections += _top_table("Top 5 Authors", top_authors.top_authors.items)
    sections += _top_table("Top 5 Keywords", kw_result.top_keywords)
    sections.append("\n---\n*Generated by Citationer · simple template*\n")
    return "\n".join(sections)


def _build_markdown(records, template: str = "academic") -> str:
    """Build a Markdown report using the named template."""
    if template == "academic":
        return _build_academic(records)
    if template == "simple":
        return _build_simple(records)
    # Fallback (shouldn't happen — typer validates choices)
    return _build_academic(records)


def _md_to_html(md: str, title: str) -> str:
    """Very simple MD → HTML (paragraph + line-break conversion)."""
    body = md.replace("\n\n", "\n</p><p>\n").replace("\n", "<br>\n")
    return (
        "<!DOCTYPE html>\n<html>\n<head>\n<meta charset=\"utf-8\">\n"
        f"<title>{title}</title>\n"
        "<style>"
        "body{font-family:Arial,sans-serif;max-width:800px;"
        "margin:0 auto;padding:20px;line-height:1.5}"
        "table{border-collapse:collapse;width:100%;margin:1em 0}"
        "td,th{border:1px solid #ddd;padding:8px;text-align:left}"
        "th{background:#f0f0f0}"
        "h1,h2{color:#222}"
        "</style>\n</head>\n<body>\n"
        f"{body}\n</body>\n</html>"
    )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command(name="quick")
def quick(
    output: Path = typer.Option(
        ..., "--output", "-o", help="输出文件路径 (.md 或 .html)"
    ),
    template: str = typer.Option(
        "academic",
        "--template",
        "-t",
        help="报告模板: academic (完整) 或 simple (简洁)",
    ),
    enhance: bool = typer.Option(
        False, "--enhance", help="使用 LLM 增强报告（生成研究发现与展望章节）"
    ),
) -> None:
    """一键生成完整文献分析报告（Markdown/HTML）。"""
    if template not in _VALID_TEMPLATES:
        console.print(
            f"[red]未知模板 '{template}'。可选: {', '.join(_VALID_TEMPLATES)}[/red]"
        )
        raise typer.Exit(1)

    records = _get_records()
    if not records:
        return

    console.print(f"[dim]正在生成报告（模板: {template}）…[/dim]")
    md = _build_markdown(records, template=template)

    # LLM enhancement
    if enhance:
        try:
            from citationer.llm.client import LLMClient, LLMConfig
            from citationer.utils.config import load_llm_config
            cfg = load_llm_config()
            if cfg["api_key"]:
                client = LLMClient(LLMConfig(
                    api_key=cfg["api_key"], model=cfg["model"],
                    base_url=cfg["base_url"],
                ))
                prompt = (
                    "Based on the bibliometric analysis above, write a "
                    "\"Research Findings and Future Outlook\" section (200-300 words) "
                    "covering key discoveries, emerging trends, and promising directions."
                )
                response = client.query(prompt, records[:50])
                md += f"\n## Research Findings and Outlook (AI-Generated)\n\n{response.content}\n"
                console.print(f"[dim]LLM 增强完成 (Token: {response.tokens_used})[/dim]")
            else:
                console.print("[yellow]LLM 未配置，跳过增强[/yellow]")
        except Exception:
            pass

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix == ".html":
        title = "Citationer Report" + (f" ({template})" if template else "")
        output.write_text(_md_to_html(md, title), encoding="utf-8")
    else:
        output.write_text(md, encoding="utf-8")

    console.print(f"[green]✅ 报告已生成: {output}[/green]")


@app.command(name="custom")
def custom(
    config_file: Path = typer.Argument(
        ..., help="报告配置 YAML 文件路径"
    ),
    output: Path = typer.Option(
        ..., "--output", "-o", help="输出文件路径"
    ),
) -> None:
    """使用自定义配置生成报告（YAML 配置文件）。"""
    records = _get_records()
    if not records:
        return

    try:
        import yaml
        cfg = yaml.safe_load(config_file.read_text(encoding="utf-8"))
    except Exception as e:
        console.print(f"[red]配置文件读取失败: {e}[/red]")
        return

    title = cfg.get("title", "Citationer Report")
    sections = cfg.get("sections", ["overview", "yearly", "journals", "authors"])
    md = f"# {title}\n\n"

    engine = StatsEngine(records)

    for sec in sections:
        if sec == "overview":
            ov = engine.overview()
            md += f"## Overview\nTotal: {ov.total_records} · h-index: {ov.h_index}\n\n"
        elif sec == "yearly":
            yr = engine.yearly()
            md += "## Yearly Trend\n\n"
            for y in sorted(yr.year_counts)[-10:]:
                md += f"- {y}: {yr.year_counts[y]}\n"
            md += "\n"
        elif sec == "journals":
            jr = engine.journals(top_n=10)
            md += "## Top Journals\n\n"
            for i, (n, c) in enumerate(jr.items, 1):
                md += f"{i}. {n} ({c})\n"
            md += "\n"
        elif sec == "authors":
            ar = engine.authors(top_n=10)
            md += "## Top Authors\n\n"
            for i, (n, c) in enumerate(ar.top_authors.items, 1):
                md += f"{i}. {n} ({c})\n"
            md += "\n"
        elif sec == "keywords":
            te = TextEngine(records)
            kw = te.keywords(top_n=10)
            md += "## Keywords\n\n"
            for kw_name, cnt in kw.top_keywords:
                md += f"- {kw_name}: {cnt}\n"
            md += "\n"
        elif sec == "topics":
            te = TextEngine(records)
            tp = te.topics(num_topics=5)
            md += "## Topic Modeling\n\n"
            for i, terms in enumerate(tp.topics):
                md += f"- Topic {i+1}: {', '.join(t[0] for t in terms[:5])}\n"
            md += "\n"

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(md, encoding="utf-8")
    console.print(f"[green]✅ 报告已生成: {output}[/green]")
