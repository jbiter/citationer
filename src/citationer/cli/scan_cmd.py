"""Scan command — detect bibliographic files in a directory."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from citationer.parsers.base import ParserRegistry
from citationer.parsers.cnki import CnkiExcelParser
from citationer.parsers.cssci import CssciParser
from citationer.parsers.pubmed import PubMedParser
from citationer.parsers.scopus import ScopusParser
from citationer.parsers.wos import WosExcelParser, WosTabDelimitedParser, WosTextParser

console = Console()

# Global parser registry (populated on first use)
_registry: ParserRegistry | None = None


def get_registry() -> ParserRegistry:
    """Get or create the parser registry with built-in parsers."""
    global _registry
    if _registry is None:
        _registry = ParserRegistry()
        _registry.register(CnkiExcelParser())
        # Tab-delimited must be checked BEFORE text parser
        _registry.register(WosTabDelimitedParser())
        _registry.register(WosTextParser())
        _registry.register(WosExcelParser())
        _registry.register(ScopusParser())
        _registry.register(PubMedParser())
        _registry.register(CssciParser())
    return _registry


def scan(
    directory: Path = typer.Argument(
        Path.cwd(),
        help="要扫描的目录路径 (默认: 当前目录)",
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive",
        "-r/-R",
        help="是否递归扫描子目录",
    ),
) -> None:
    """扫描目录下的题录文件，自动识别格式和来源。"""
    if not directory.exists():
        console.print(f"[red]❌ 目录不存在: {directory}[/red]")
        raise typer.Exit(1)

    registry = get_registry()

    # Collect files
    files: list[Path] = []
    if recursive:
        supported_exts = {
            ".xlsx", ".xls", ".txt", ".ciw", ".csv",
            ".bib", ".ris", ".xml", ".nbib", ".rdf",
        }
        for ext in supported_exts:
            files.extend(directory.rglob(f"*{ext}"))
    else:
        for f in directory.iterdir():
            if f.is_file():
                files.append(f)

    files = sorted(set(files))

    if not files:
        console.print("[yellow]📁 未找到支持的题录文件[/yellow]")
        return

    # Build scan results
    table = Table(
        title=f"📁 扫描结果: {directory}",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("文件名", style="dim")
    table.add_column("来源", justify="center")
    table.add_column("条目数", justify="right")
    table.add_column("年份范围", justify="center")

    total_records = 0
    sources_found: set[str] = set()
    unknown_count = 0

    for filepath in files:
        parser = registry.find_parser(filepath)
        if parser:
            source = parser.source_name
            sources_found.add(source)
            try:
                records = parser.parse(filepath)
                count = len(records)
                total_records += count

                years = [r.year for r in records if r.year is not None]
                year_range = f"{min(years)} - {max(years)}" if years else "-"

                table.add_row(
                    filepath.name,
                    f"[green]{source}[/green]",
                    str(count),
                    year_range,
                )
            except Exception:
                table.add_row(
                    filepath.name,
                    f"[green]{source}[/green]",
                    "[yellow]解析失败[/yellow]",
                    "-",
                )
        else:
            unknown_count += 1
            table.add_row(
                filepath.name,
                "[red]❓ 未知[/red]",
                "-",
                "-",
            )

    console.print(table)

    # Summary
    summary_parts = [f"总计: [bold]{total_records}[/bold] 条记录"]
    if sources_found:
        summary_parts.append(f"{len(sources_found)} 个来源 ({', '.join(sorted(sources_found))})")
    if unknown_count > 0:
        summary_parts.append(f"[yellow]{unknown_count} 个无法识别的文件[/yellow]")

    console.print("  " + " · ".join(summary_parts))


def status_cmd(
    directory: Path = typer.Argument(
        Path.cwd(),
        help="要检查的目录路径 (默认: 当前目录)",
    ),
) -> None:
    """查看当前目录的扫描状态（快速版 scan）。"""
    scan(directory, recursive=False)
