"""Configuration management commands."""

from __future__ import annotations

import os

import typer
from rich.console import Console
from rich.table import Table

from citationer.utils.config import (
    CitationerConfig,
    get_config_path,
    load_llm_config,
)

app = typer.Typer(
    name="config",
    help="配置管理",
    no_args_is_help=True,
)

console = Console()

# Known config keys and their descriptions
_LLM_KEYS: dict[str, dict] = {
    "llm.api_key": {
        "description": "LLM API Key（必填）",
        "example": "sk-xxxx",
        "sensitive": True,
    },
    "llm.model": {
        "description": "模型名称",
        "example": "deepseek-chat / gpt-4o / llama3",
    },
    "llm.base_url": {
        "description": "API 端点 URL",
        "example": "https://api.deepseek.com",
    },
    "llm.temperature": {
        "description": "生成温度 (0.0-2.0)，越低越确定",
        "example": "0.3",
    },
    "llm.max_tokens": {
        "description": "最大输出 Token 数",
        "example": "4096",
    },
}


def _mask_value(value: str) -> str:
    """Mask sensitive values for display."""
    if len(value) > 12:
        return value[:8] + "…" + value[-4:]
    if len(value) > 4:
        return value[:2] + "…" + value[-2:]
    return "***" if value else ""


# ------------------------------------------------------------------
# config show
# ------------------------------------------------------------------


@app.command(name="show")
def show() -> None:
    """显示当前所有配置。"""
    config_path = get_config_path()
    cfg = load_llm_config()

    # ---- Config file status ----
    if config_path.exists():
        console.print(f"[dim]配置文件: {config_path}[/dim]")
    else:
        console.print(f"[yellow]配置文件未创建: {config_path}[/yellow]")

    # ---- LLM Config ----
    console.print()
    table = Table(
        title="🤖 LLM 配置",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("配置项", style="dim")
    table.add_column("当前值")
    table.add_column("来源")

    env_key = (
        os.environ.get("CITATIONER_LLM_API_KEY", "")
        or os.environ.get("DEEPSEEK_API_KEY", "")
    )
    env_model = os.environ.get("CITATIONER_LLM_MODEL", "")
    env_url = os.environ.get("CITATIONER_LLM_BASE_URL", "")
    env_temp = os.environ.get("CITATIONER_LLM_TEMPERATURE", "")
    env_tokens = os.environ.get("CITATIONER_LLM_MAX_TOKENS", "")

    api_key = cfg["api_key"]
    if api_key:
        key_display = f"[green]{_mask_value(api_key)}[/green]"
    else:
        key_display = "[red]未配置[/red]"
    table.add_row("API Key", key_display, _src(env_key))

    model_display = cfg["model"]
    table.add_row("模型", model_display, _src(env_model))

    url_display = cfg["base_url"]
    table.add_row("端点", url_display, _src(env_url))

    temp_display = str(cfg["temperature"])
    table.add_row("Temperature", temp_display, _src(env_temp))

    tokens_display = str(cfg["max_tokens"])
    table.add_row("Max Tokens", tokens_display, _src(env_tokens))

    console.print(table)

    # ---- Other config ----
    console.print()
    other = Table(
        title="⚙ 其他配置",
        show_header=True,
        header_style="bold",
    )
    other.add_column("配置项", style="dim")
    other.add_column("值")

    full_cfg = CitationerConfig.load(config_path) if config_path.exists() else CitationerConfig()
    other.add_row("语言", full_cfg.language)
    other.add_row("默认输出目录", full_cfg.default_output_dir)
    other.add_row("标题相似度阈值（高）", str(full_cfg.title_similarity_high))
    other.add_row("标题相似度阈值（低）", str(full_cfg.title_similarity_low))

    console.print(other)

    # ---- Help ----
    console.print()
    console.print(
        "[dim]修改配置: [/dim]"
        "[bold]citationer config set <key> <value>[/bold]   "
        "[dim]示例: [/dim]"
        "[bold]citationer config set llm.api_key sk-xxxx[/bold]"
    )


# ------------------------------------------------------------------
# config set
# ------------------------------------------------------------------


@app.command(name="set")
def set_config(
    key: str = typer.Argument(..., help="配置键，如 llm.api_key、llm.model"),
    value: str = typer.Argument(..., help="配置值"),
) -> None:
    """设置配置项的值并保存到配置文件。"""
    config_path = get_config_path()

    # Load existing or create new
    cfg = CitationerConfig.load(config_path) if config_path.exists() else CitationerConfig()

    attr: str = ""
    typed_value: str | int | float | bool = value

    parts = key.split(".")
    if len(parts) == 2 and parts[0] == "llm":
        attr = parts[1]
        if not hasattr(cfg.llm, attr):
            console.print(f"[red]❌ 未知的 LLM 配置项: {attr}[/red]")
            console.print(f"[dim]可用的 LLM 配置项: {', '.join(_LLM_KEYS)}[/dim]")
            raise typer.Exit(1)

        # Type conversion
        field_type = type(getattr(cfg.llm, attr))
        if field_type is bool:
            typed_value = value.lower() in ("true", "1", "yes")
        elif field_type is int:
            try:
                typed_value = int(value)
            except ValueError:
                console.print(f"[red]❌ {key} 需要整数值，收到: {value}[/red]")
                raise typer.Exit(1)
        elif field_type is float:
            try:
                typed_value = float(value)
            except ValueError:
                console.print(f"[red]❌ {key} 需要浮点数值，收到: {value}[/red]")
                raise typer.Exit(1)
        else:
            typed_value = value

        setattr(cfg.llm, attr, typed_value)
    elif key == "language":
        cfg.language = value
        typed_value = value
    elif key == "default_output_dir":
        cfg.default_output_dir = value
        typed_value = value
    elif key == "title_similarity_high":
        typed_value = float(value)
        cfg.title_similarity_high = typed_value
    elif key == "title_similarity_low":
        typed_value = float(value)
        cfg.title_similarity_low = typed_value
    else:
        console.print(f"[red]❌ 未知的配置项: {key}[/red]")
        console.print(
            "[dim]可用的配置项: llm.api_key, llm.model, llm.base_url, "
            "llm.temperature, llm.max_tokens, language, default_output_dir[/dim]"
        )
        raise typer.Exit(1)

    cfg.save(config_path)

    # Display the set value (mask if sensitive)
    if attr == "api_key":
        display_val = _mask_value(value)
    else:
        display_val = str(typed_value)
    console.print(f"[green]✅ {key} = {display_val}[/green]")
    console.print(f"[dim]已保存到 {config_path}[/dim]")


# ------------------------------------------------------------------
# config init
# ------------------------------------------------------------------


@app.command(name="init")
def init(
    force: bool = typer.Option(
        False, "--force", "-f", help="覆盖已有配置文件"
    ),
) -> None:
    """初始化配置文件（使用默认值）。"""
    config_path = get_config_path()

    if config_path.exists() and not force:
        console.print(
            f"[yellow]配置文件已存在: {config_path}[/yellow]\n"
            "使用 [bold]--force[/bold] 覆盖"
        )
        return

    cfg = CitationerConfig()
    cfg.save(config_path)
    console.print(f"[green]✅ 配置文件已创建: {config_path}[/green]")
    console.print()
    console.print(
        "[dim]接下来: [/dim]"
        "[bold]citationer config set llm.api_key <your-key>[/bold]"
    )


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------


def _src(env_val: str) -> str:
    """Return a label showing the configuration source."""
    if env_val:
        return "[green]env[/green]"
    if get_config_path().exists():
        return "[yellow]config[/yellow]"
    return "[dim]default[/dim]"
