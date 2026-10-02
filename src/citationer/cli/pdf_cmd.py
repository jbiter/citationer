"""PDF analysis commands."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from citationer.analysis.text import TextEngine
from citationer.models.record import Record
from citationer.pdf.extractor import PdfExtractor

app = typer.Typer(
    name="pdf",
    help="PDF 全文分析",
    no_args_is_help=True,
)

console = Console()


def _ensure_pypdf() -> None:
    """Fail fast with a helpful message if pypdf is not installed."""
    try:
        import pypdf  # noqa: F401
    except ImportError as exc:
        console.print(
            "[red]PDF 功能需要 pypdf 库。[/red]\n"
            "请运行: pip install \"citationer[text]\" 或 pip install pypdf"
        )
        raise typer.Exit(code=1) from exc


def _ensure_text_deps() -> None:
    """Fail fast with a helpful message if NLP deps are not installed."""
    missing: list[str] = []
    for module, package in (
        ("jieba", "jieba"),
        ("gensim", "gensim"),
        ("sklearn", "scikit-learn"),
    ):
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    if missing:
        console.print(
            f"[red]主题建模需要以下库: {', '.join(missing)}[/red]\n"
            "请运行: pip install \"citationer[text]\""
        )
        raise typer.Exit(code=1)


@app.command(name="extract")
def extract_command(
    directory: Path = typer.Argument(
        ...,
        help="PDF 文件目录",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    output: Path = typer.Option(
        Path("pdf_texts.json"),
        "--output",
        "-o",
        help="输出 JSON 文件",
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive",
        help="是否递归子目录",
    ),
    max_chars: int = typer.Option(
        0,
        "--max-chars",
        "-m",
        help="单个文件最大字符数（0 为不截断）",
    ),
) -> None:
    """提取一个目录下所有 PDF 的文本内容。"""
    _ensure_pypdf()
    extractor = PdfExtractor(recursive=recursive, max_chars=max_chars)
    result = extractor.extract_directory(directory)

    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    output.write_text(output_json, encoding="utf-8")

    summary = result["summary"]
    console.print(
        f"[green]✓ 处理完成：{summary['success']} 成功，"
        f"{summary['failed']} 失败，共 {summary['total']} 个文件[/green]"
    )
    console.print(f"[dim]结果已保存到 {output}[/dim]")


@app.command(name="topics")
def topics_command(
    directory: Path = typer.Argument(
        ...,
        help="PDF 文件目录",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    num_topics: int | None = typer.Option(
        None,
        "--num-topics",
        "-k",
        help="主题数量（不指定则自动确定）",
    ),
    max_terms: int = typer.Option(
        10,
        "--max-terms",
        "-t",
        help="每个主题显示的关键词数",
    ),
    method: str = typer.Option(
        "lda",
        "--method",
        "-m",
        help="主题模型: lda, nmf",
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive",
        help="是否递归子目录",
    ),
    max_chars: int = typer.Option(
        0,
        "--max-chars",
        help="单个文件最大字符数（0 为不截断）",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="保存 JSON 结果到文件",
    ),
) -> None:
    """对目录下所有 PDF 的全文进行主题建模。"""
    _ensure_pypdf()
    _ensure_text_deps()

    extractor = PdfExtractor(recursive=recursive, max_chars=max_chars)
    result = extractor.extract_directory(directory)

    docs = [
        Record(title=f["filename"], abstract=f["text"])
        for f in result["files"]
        if f["text"].strip()
    ]
    skipped = sum(1 for f in result["files"] if not f["text"].strip())

    if result["errors"]:
        console.print(
            f"[yellow]⚠ {len(result['errors'])} 个文件提取失败，已跳过[/yellow]"
        )
    if skipped:
        console.print(f"[yellow]⚠ {skipped} 个文件文本为空，已跳过[/yellow]")

    if not docs:
        console.print("[red]没有可分析的 PDF 文本[/red]")
        raise typer.Exit(code=1)

    console.print(f"[dim]正在对 {len(docs)} 篇全文运行 {method.upper()} 主题建模…[/dim]")
    engine = TextEngine(docs)
    tm = engine.topics(num_topics=num_topics, max_terms=max_terms, method=method)

    if not tm.topics:
        console.print("[yellow]未能发现主题，请检查文本量是否足够[/yellow]")
        raise typer.Exit(code=1)

    score_info = ""
    if tm.coherence_score is not None:
        score_info = f" · 一致性分数: {tm.coherence_score:.3f}"

    console.print()
    console.print(
        f"[bold]发现 {tm.num_topics} 个主题[/bold] "
        f"({tm.method.upper()}){score_info}"
    )
    console.print()

    table = Table(
        title="🧠 PDF 全文主题建模结果",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("主题", justify="center")
    table.add_column(f"关键词 (Top-{max_terms})")

    for i, topic_terms in enumerate(tm.topics):
        term_str = ", ".join(t for t, _ in topic_terms[:max_terms])
        table.add_row(f"Topic {i + 1}", term_str)

    console.print(table)

    if output:
        json_data = {
            "method": tm.method,
            "num_topics": tm.num_topics,
            "coherence_score": tm.coherence_score,
            "documents": len(docs),
            "topics": [
                [{"term": t, "weight": w} for t, w in topic]
                for topic in tm.topics
            ],
        }
        json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
        output.write_text(json_str, encoding="utf-8")
        console.print(f"[green]结果已保存到 {output}[/green]")
