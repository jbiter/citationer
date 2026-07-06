"""Main CLI entry point for citationer.

Help system (PRD v2.0 F-8.2):
  L1: citationer --help          → Custom Rich-formatted overview
  L2: citationer <grp> --help     → rich-click rendered group help
  L3: citationer <grp> <cmd> --help → rich-click rendered command help
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from typer.core import TyperGroup

# rich-click enhances Typer's built-in --help with Rich formatting (L2 & L3).
try:
    import rich_click  # noqa: F401
except ImportError:
    pass

from citationer.cli import (
    ai_cmd,
    clean_cmd,
    config_cmd,
    export_cmd,
    import_cmd,
    network_cmd,
    report_cmd,
    scan_cmd,
    stats_cmd,
    text_cmd,
    trend_cmd,
)
from citationer.cli.help import render_l1_overview


class _RootGroup(TyperGroup):
    """Custom TyperGroup that shows our L1 overview for top-level --help.

    Sub-groups and sub-commands keep the default behaviour (L2 & L3),
    which rich-click automatically enhances with Rich formatting.
    """

    def get_help(self, ctx: typer.Context) -> str:  # type: ignore[override]
        if ctx.parent is None:
            render_l1_overview()
            ctx.exit()
            return ""
        return super().get_help(ctx)

    def parse_args(self, ctx, args):
        # Intercept --version before anything else
        if "--version" in args:
            from citationer import __version__
            console.print(f"citationer v{__version__}")
            ctx.exit()
        return super().parse_args(ctx, args)


app = typer.Typer(
    name="citationer",
    help="一键式文献题录分析 CLI 工具",
    add_completion=True,
    no_args_is_help=True,
    cls=_RootGroup,
)

console = Console()

# Register top-level commands
app.command(name="scan")(scan_cmd.scan)
app.command(name="status")(scan_cmd.status_cmd)
app.command(name="import")(import_cmd.import_data)
app.command(name="clean")(clean_cmd.clean)

# Register command groups
app.add_typer(stats_cmd.app, name="stats")
app.add_typer(text_cmd.app, name="text")
app.add_typer(ai_cmd.app, name="ai")
app.add_typer(network_cmd.app, name="network")
app.add_typer(config_cmd.app, name="config")
app.add_typer(export_cmd.app, name="export")
app.add_typer(trend_cmd.app, name="trend")
app.add_typer(report_cmd.app, name="report")


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



