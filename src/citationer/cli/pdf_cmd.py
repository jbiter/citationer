"""PDF analysis commands."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

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
