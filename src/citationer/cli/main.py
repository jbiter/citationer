"""Main CLI entry point for citationer."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from citationer.cli import clean_cmd, import_cmd, scan_cmd, stats_cmd

app = typer.Typer(
    name="citationer",
    help="一键式文献题录分析 CLI 工具",
    add_completion=True,
    no_args_is_help=True,
)

console = Console()

# Register subcommands
app.command(name="scan")(scan_cmd.scan)
app.command(name="status")(scan_cmd.status_cmd)
app.command(name="import")(import_cmd.import_data)
app.command(name="clean")(clean_cmd.clean)

# Stats subcommand group
app.add_typer(stats_cmd.app, name="stats")


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="详细输出（调试模式）"
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="安静模式（仅输出结果数据）"
    ),
    output_dir: Path | None = typer.Option(
        None, "--output", "-o", help="指定输出目录"
    ),
    no_color: bool = typer.Option(
        False, "--no-color", help="禁用彩色输出"
    ),
) -> None:
    """Citationer — 文献题录分析工具

    进入包含题录文件的目录，运行命令，即可获得文献分析报告。
    """
    if no_color:
        console.no_color = True


if __name__ == "__main__":
    app()
