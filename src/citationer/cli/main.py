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

from citationer.cli.help import render_l1_overview

# ── Lazy command imports ──────────────────────────────────────────
# All CLI modules are imported on first use instead of at startup,
# cutting CLI load time from ~400ms to ~150ms.

def _import_scan():
    from citationer.cli import scan_cmd
    return scan_cmd

def _import_clean():
    from citationer.cli import clean_cmd
    return clean_cmd

def _import_import():
    from citationer.cli import import_cmd
    return import_cmd

def _import_stats():
    from citationer.cli import stats_cmd
    return stats_cmd

def _import_text():
    from citationer.cli import text_cmd
    return text_cmd

def _import_ai():
    from citationer.cli import ai_cmd
    return ai_cmd

def _import_network():
    from citationer.cli import network_cmd
    return network_cmd

def _import_config():
    from citationer.cli import config_cmd
    return config_cmd

def _import_export():
    from citationer.cli import export_cmd
    return export_cmd

def _import_trend():
    from citationer.cli import trend_cmd
    return trend_cmd

def _import_report():
    from citationer.cli import report_cmd
    return report_cmd

def _import_interactive():
    from citationer.cli import interactive_cmd
    return interactive_cmd

def _import_run():
    from citationer.cli import run_cmd
    return run_cmd


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


class _LazyTyper(typer.Typer):
    """Typer subclass that lazily registers commands on first invocation."""

    def __call__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        _register()
        return super().__call__(*args, **kwargs)


app = _LazyTyper(
    name="citationer",
    help="文献题录分析 CLI 工具",
    add_completion=True,
    no_args_is_help=True,
    cls=_RootGroup,
)

console = Console()


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
    config_path: Path | None = typer.Option(
        None, "--config", "-c", help="指定配置文件路径"
    ),
) -> None:
    """Citationer — 文献题录分析工具

    进入包含题录文件的目录，运行命令，即可获得文献分析报告。
    """
    if no_color:
        console.no_color = True


# ── Register commands with lazy imports ───────────────────────────

def _register():
    """Register all commands. Called once on first dispatch."""
    if _register._done:  # type: ignore[attr-defined]
        return
    _register._done = True  # type: ignore[attr-defined]

    scan = _import_scan()
    imp = _import_import()
    clean = _import_clean()
    app.command(name="scan")(scan.scan)
    app.command(name="status")(scan.status_cmd)
    app.command(name="import")(imp.import_data)
    app.command(name="clean")(clean.clean)
    app.add_typer(_import_stats().app, name="stats")
    app.add_typer(_import_text().app, name="text")
    app.add_typer(_import_ai().app, name="ai")
    app.add_typer(_import_network().app, name="network")
    app.add_typer(_import_config().app, name="config")
    app.add_typer(_import_export().app, name="export")
    app.add_typer(_import_trend().app, name="trend")
    app.add_typer(_import_report().app, name="report")
    app.add_typer(_import_interactive().app, name="interactive")
    app.add_typer(_import_run().app, name="run")

_register._done = False  # type: ignore[attr-defined]


if __name__ == "__main__":
    app()
