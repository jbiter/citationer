"""Text NLP commands — preprocessing, keywords, topics, summarization, clustering."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from citationer.analysis.text import TextEngine
from citationer.utils.db_loader import get_records

app = typer.Typer(
    name="text",
    help="文本挖掘与 NLP 分析",
    no_args_is_help=True,
)

console = Console()


_get_records = get_records


# ------------------------------------------------------------------
# preprocess
# ------------------------------------------------------------------


@app.command(name="preprocess")
def preprocess(
    field: str = typer.Option(
        "all", "--field", "-f",
        help="要处理的字段: title, abstract, all",
    ),
    lang: str = typer.Option(
        "auto", "--lang", "-l",
        help="语言: zh, en, auto（自动检测）",
    ),
    top_n: int = typer.Option(
        20, "--top", "-n",
        help="显示前 N 条记录的处理结果",
    ),
) -> None:
    """文本预处理：分词、去停用词、语言检测。"""
    records = _get_records()
    if not records:
        return

    engine = TextEngine(records)
    results = engine.preprocess(field=field, lang=lang)

    # Summary
    zh_count = sum(1 for r in results if r.language == "zh")
    en_count = sum(1 for r in results if r.language == "en")
    total_tokens = sum(r.token_count for r in results)

    console.print()
    summary = Table(title="📝 预处理概览", show_header=True, header_style="bold cyan")
    summary.add_column("指标")
    summary.add_column("数值", justify="right")
    summary.add_row("总记录数", str(len(results)))
    summary.add_row("中文记录", str(zh_count))
    summary.add_row("英文记录", str(en_count))
    summary.add_row("总 Token 数", str(total_tokens))
    summary.add_row("平均 Token/篇", f"{total_tokens / max(len(results), 1):.0f}")
    console.print(summary)

    # Sample tokens from top N records
    console.print()
    sample_table = Table(
        title=f"📋 分词样例 (前 {min(top_n, len(results))} 条)",
        show_header=True,
        header_style="bold",
    )
    sample_table.add_column("#", justify="right", style="dim")
    sample_table.add_column("文献标题")
    sample_table.add_column("语言", justify="center")
    sample_table.add_column("Token 数", justify="right")
    sample_table.add_column("Token 样例")

    for i, r in enumerate(results[:top_n], 1):
        title_short = r.title[:50] + "…" if len(r.title) > 50 else r.title
        sample = ", ".join(r.tokens[:8])
        if len(r.tokens) > 8:
            sample += "…"
        sample_table.add_row(str(i), title_short, r.language, str(r.token_count), sample)

    console.print(sample_table)


# ------------------------------------------------------------------
# keywords
# ------------------------------------------------------------------


@app.command(name="keywords")
def keywords(
    top_n: int = typer.Option(50, "--top", "-n", help="显示 Top-N 关键词"),
    per_year: bool = typer.Option(
        False, "--per-year", help="显示关键词年代分布"
    ),
    min_count: int = typer.Option(
        1, "--min-count", "-m", help="关键词最小出现次数"
    ),
    output_format: str = typer.Option(
        "table", "--format", "-f", help="输出格式: table, json, csv"
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="保存到文件"
    ),
) -> None:
    """关键词频次统计与年代分布分析。"""
    records = _get_records()
    if not records:
        return

    engine = TextEngine(records)
    result = engine.keywords(top_n=top_n, per_year=per_year, min_count=min_count)

    if not result.top_keywords:
        console.print("[yellow]没有找到关键词数据[/yellow]")
        return

    if output_format == "json":
        data = {
            "total_unique": result.total_unique,
            "keywords": [{"keyword": k, "count": c} for k, c in result.top_keywords],
        }
        if per_year:
            data["yearly"] = {
                k: dict(v) for k, v in result.yearly_distribution.items()
            }
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        if output_file:
            output_file.write_text(json_str, encoding="utf-8")
            console.print(f"[green]已保存到 {output_file}[/green]")
        else:
            console.print_json(json_str)
        return

    # Table output
    table = Table(
        title=f"🔑 Top-{top_n} 高频关键词",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("关键词")
    table.add_column("频次", justify="right")
    table.add_column("占比", justify="right")

    total = sum(c for _, c in result.top_keywords)
    for i, (kw, count) in enumerate(result.top_keywords, 1):
        pct = f"{count / max(total, 1) * 100:.1f}%"
        table.add_row(str(i), kw, str(count), pct)

    console.print(table)
    if result.top_keywords:
        top_sum = sum(c for _, c in result.top_keywords)
        coverage = total / max(top_sum, 1) * 100
    else:
        coverage = 0.0
    console.print(
        f"共 [bold]{result.total_unique}[/bold] 个不同关键词, "
        f"Top-{top_n} 累计占比 [bold]{coverage:.0f}%[/bold]"
    )

    if per_year and result.yearly_distribution:
        console.print()
        _print_yearly_heatmap(result.top_keywords[:20], result.yearly_distribution)


def _print_yearly_heatmap(
    top_kw: list[tuple[str, int]],
    yearly: dict[str, dict[int, int]],
) -> None:
    """Print a simplified keyword × year heatmap table.

    Only shows the most recent 12 years to keep the table readable.
    """
    all_years: set[int] = set()
    for kw, _ in top_kw:
        if kw in yearly:
            all_years.update(yearly[kw].keys())

    if not all_years:
        return

    years = sorted(all_years)
    # Limit to the most recent 12 years for display
    if len(years) > 12:
        years = years[-12:]

    table = Table(
        title=f"📅 关键词年代分布 (近 {len(years)} 年)",
        show_header=True,
        header_style="bold",
    )
    table.add_column("关键词", style="dim", min_width=16, max_width=22)
    for y in years:
        table.add_column(str(y), justify="right")

    for kw, _ in top_kw[:15]:
        kw_short = kw[:20] + "…" if len(kw) > 20 else kw
        row = [kw_short]
        kw_yearly = yearly.get(kw, {})
        for y in years:
            count = kw_yearly.get(y, 0)
            row.append(str(count) if count else "-")
        table.add_row(*row)

    console.print(table)


# ------------------------------------------------------------------
# topics
# ------------------------------------------------------------------


@app.command(name="topics")
def topics(
    num_topics: int | None = typer.Option(
        None, "--num-topics", "-k",
        help="主题数量（不指定则自动确定）",
    ),
    max_terms: int = typer.Option(
        10, "--max-terms", "-t",
        help="每个主题显示的关键词数",
    ),
    method: str = typer.Option(
        "lda", "--method", "-m",
        help="主题模型: lda, nmf",
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="保存 JSON 结果到文件"
    ),
) -> None:
    """主题建模：LDA/NMF 主题发现与关键词提取。"""
    records = _get_records()
    if not records:
        return

    console.print(f"[dim]正在运行 {method.upper()} 主题建模…[/dim]")
    engine = TextEngine(records)
    result = engine.topics(num_topics=num_topics, max_terms=max_terms, method=method)

    if not result.topics:
        console.print("[yellow]未能发现主题，请检查数据量是否足够[/yellow]")
        return

    score_info = ""
    if result.coherence_score is not None:
        score_info = f" · 一致性分数: {result.coherence_score:.3f}"

    console.print()
    console.print(
        f"[bold]发现 {result.num_topics} 个主题[/bold] "
        f"({result.method.upper()}){score_info}"
    )
    console.print()

    # Render as a table for clean output
    table = Table(
        title="🧠 主题建模结果",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("主题", justify="center")
    table.add_column(f"关键词 (Top-{max_terms})")
    table.add_column("一致性", justify="center")

    for i, topic_terms in enumerate(result.topics):
        term_str = ", ".join(t for t, _ in topic_terms[:max_terms])
        coh = f"{result.coherence_score:.3f}" if result.coherence_score else "-"
        table.add_row(f"Topic {i + 1}", term_str, coh)

    console.print(table)

    # Optional JSON export
    if output_file:
        json_data = {
            "method": result.method,
            "num_topics": result.num_topics,
            "coherence_score": result.coherence_score,
            "topics": [
                [{"term": t, "weight": w} for t, w in topic]
                for topic in result.topics
            ],
        }
        json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
        output_file.write_text(json_str, encoding="utf-8")
        console.print(f"[green]结果已保存到 {output_file}[/green]")


# ------------------------------------------------------------------
# summarize
# ------------------------------------------------------------------


@app.command(name="summarize")
def summarize(
    max_sentences: int = typer.Option(
        10, "--max-sentences", "-n",
        help="提取的关键句数量",
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="保存到文本文件"
    ),
) -> None:
    """提取式摘要：基于 TF-IDF 的关键句提取（无需 LLM）。"""
    records = _get_records()
    if not records:
        return

    engine = TextEngine(records)
    result = engine.summarize(max_sentences=max_sentences)

    if not result.sentences:
        console.print("[yellow]未能提取摘要句[/yellow]")
        return

    console.print()
    console.print(
        Panel.fit(
            f"从 [bold]{len(records)}[/bold] 篇文献中提取了 "
            f"[bold]{len(result.sentences)}[/bold] 个关键句",
            title="📄 文献速览",
            border_style="cyan",
        )
    )

    for i, (sentence, score) in enumerate(result.sentences, 1):
        console.print(f"  [bold cyan]{i}.[/bold cyan] [dim]({score:.4f})[/dim] {sentence}")

    if output_file:
        content = "\n\n".join(
            f"{i}. [{score:.4f}] {sentence}"
            for i, (sentence, score) in enumerate(result.sentences, 1)
        )
        output_file.write_text(content, encoding="utf-8")
        console.print(f"\n[green]已保存到 {output_file}[/green]")


# ------------------------------------------------------------------
# cluster
# ------------------------------------------------------------------


@app.command(name="cluster")
def cluster(
    method: str = typer.Option(
        "kmeans", "--method", "-m",
        help="聚类方法: kmeans, hierarchical",
    ),
    n_clusters: int | None = typer.Option(
        None, "--n-clusters", "-k",
        help="聚类数（不指定则自动确定）",
    ),
    vectorizer: str = typer.Option(
        "tfidf", "--vectorizer", "-v",
        help="向量化方法: tfidf, sbert",
    ),
    output_file: Path | None = typer.Option(
        None, "--output", "-o", help="保存聚类结果 CSV 文件"
    ),
) -> None:
    """文献聚类：基于标题+摘要的 K-Means 或层次聚类。"""
    records = _get_records()
    if not records:
        return

    console.print(f"[dim]正在运行 {method} 聚类…[/dim]")
    engine = TextEngine(records)
    result = engine.cluster(method=method, n_clusters=n_clusters, vectorizer=vectorizer)

    if not result.labels:
        console.print("[yellow]聚类失败，请检查数据[/yellow]")
        return

    # Cluster summary
    table = Table(
        title=f"🔬 聚类结果 ({result.method}, {result.n_clusters} 类)",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("类别", justify="center")
    table.add_column("文献数", justify="right")
    table.add_column("占比", justify="right")
    table.add_column("代表词")

    total = len(result.labels)
    for cid in sorted(result.cluster_sizes.keys()):
        size = result.cluster_sizes[cid]
        pct = f"{size / max(total, 1) * 100:.1f}%"
        terms = ", ".join(result.cluster_terms.get(cid, []))
        table.add_row(f"Cluster {cid}", str(size), pct, terms)

    console.print(table)

    if result.silhouette_score is not None:
        console.print(f"轮廓系数: [bold]{result.silhouette_score:.3f}[/bold]")

    # Optional CSV export
    if output_file:
        lines = ["record_index,cluster_label,title"]
        for i, (r, label) in enumerate(zip(records, result.labels)):
            title = r.title.replace('"', '""')
            lines.append(f'{i},"{label}","{title}"')
        output_file.write_text("\n".join(lines), encoding="utf-8")
        console.print(f"[green]聚类结果已保存到 {output_file}[/green]")
