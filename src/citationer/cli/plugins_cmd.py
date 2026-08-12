"""Plugin management commands."""

from __future__ import annotations

import logging

import typer
from rich.console import Console
from rich.table import Table

from citationer.cli.scan_cmd import get_registry

app = typer.Typer(
    name="plugins",
    help="管理第三方插件",
    no_args_is_help=True,
)

console = Console()
logger = logging.getLogger(__name__)


@app.command(name="list")
def list_plugins() -> None:
    """列出所有已注册的解析器（内置 + 插件）。"""
    registry = get_registry()

    table = Table(title="已注册的解析器")
    table.add_column("来源", style="dim")
    table.add_column("解析器")

    # 内置解析器：无法直接区分，因此通过 source_name 去重展示
    # 实际来源信息通过扫描 entry_points 获得
    from citationer.parsers.base import entry_points

    plugin_sources: dict[str, str] = {}
    try:
        eps = entry_points(group="citationer.parsers")
        for ep in eps:
            try:
                parser = ep.load()()
                plugin_sources[parser.source_name] = ep.dist.name if ep.dist else "plugin"
            except Exception as exc:  # noqa: BLE001
                logger.debug("Could not inspect plugin %s: %s", ep.name, exc)
    except Exception:  # noqa: BLE001
        pass

    for parser in registry:
        source = plugin_sources.get(parser.source_name, "built-in")
        table.add_row(source, parser.source_name)

    console.print(table)
