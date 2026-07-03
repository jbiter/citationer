"""AI-powered analysis commands via DeepSeek LLM."""

from __future__ import annotations

import os

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from citationer.analysis.text import TextEngine
from citationer.llm.client import LLMClient, LLMConfig
from citationer.utils.config import get_db_path, load_llm_config
from citationer.utils.db_loader import get_records

app = typer.Typer(
    name="ai",
    help="LLM 驱动的深度语义分析",
    no_args_is_help=True,
)

console = Console()


def _source_label(env_val: str) -> str:
    """Return a label showing the configuration source."""
    if env_val:
        return "[green]环境变量[/green]"
    from citationer.utils.config import get_config_path
    if get_config_path().exists():
        return "[yellow]配置文件[/yellow]"
    return "[dim]默认值[/dim]"


_get_records = get_records


def _get_client(*, dry_run: bool = False) -> LLMClient | None:
    """Create an LLM client from environment/config, or return None if not configured.

    When dry_run is True, an empty API key is accepted (no real API call made).
    """
    cfg = load_llm_config()
    if not cfg["api_key"]:
        if dry_run:
            return LLMClient(LLMConfig(api_key="dry-run-skip"))
        console.print(
            "[red]❌ LLM API Key 未配置[/red]\n"
            "运行 [bold]citationer config set llm.api_key <your-key>[/bold] 进行配置"
        )
        return None
    return LLMClient(
        LLMConfig(
            api_key=cfg["api_key"],
            model=cfg["model"],
            base_url=cfg["base_url"],
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
        )
    )


# ------------------------------------------------------------------
# ai topics --auto-label
# ------------------------------------------------------------------


@app.command(name="topics")
def topics(
    num_topics: int | None = typer.Option(
        None, "--num-topics", "-k", help="主题数量（不指定则自动确定）"
    ),
    auto_label: bool = typer.Option(
        True, "--auto-label/--no-auto-label", help="使用 LLM 为主题生成可读标签"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="预览将发送给 LLM 的内容，不实际调用 API"
    ),
) -> None:
    """LLM 驱动的主题分析：自动为主题生成人类可读的标签。"""
    records = _get_records()
    if not records:
        return

    client = _get_client(dry_run=dry_run)
    if client is None:
        return

    # First run topic modeling locally
    console.print("[dim]正在运行 LDA 主题建模…[/dim]")
    engine = TextEngine(records)
    topic_result = engine.topics(num_topics=num_topics, method="lda")

    if not topic_result.topics:
        console.print("[yellow]未能发现主题[/yellow]")
        return

    topic_terms_list: list[str] = []
    for i, terms in enumerate(topic_result.topics):
        term_str = ", ".join(t for t, _ in terms)
        topic_terms_list.append(f"Topic {i + 1}: {term_str}")

    if auto_label:
        prompt = (
            "The following are topics discovered from a collection of academic papers. "
            "For each topic, generate a concise, human-readable label (1-5 words) "
            "that best describes the research area. "
            "Return the result as a JSON object mapping topic index to label.\n\n"
            + "\n".join(topic_terms_list)
        )
        console.print("[dim]正在调用 LLM 生成主题标签…[/dim]")

        # Only send the topic terms as context, not all records.
        # The LDA topic keywords in the prompt are sufficient for labeling.
        response = client.query(prompt, [], dry_run=dry_run)

        if dry_run:
            console.print("[yellow]🔍 Dry-run 模式:[/yellow]")
            console.print_json(response.content)
            return

        if response.cached:
            console.print("[dim](结果来自缓存)[/dim]")

        console.print()
        table = Table(
            title="🏷 LLM 主题标签",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("主题", justify="center")
        table.add_column("原始关键词")
        table.add_column("LLM 生成的标签", style="bold green")

        for i, terms in enumerate(topic_result.topics):
            term_str = ", ".join(t for t, _ in terms[:5])
            table.add_row(
                f"Topic {i + 1}",
                term_str,
                "(见下方 LLM 输出)",
            )
        console.print(table)

        console.print()
        console.print(
            Panel(
                response.content,
                title="LLM 主题标签输出",
                border_style="green",
            )
        )
        console.print(f"[dim]Token 消耗: {response.tokens_used}[/dim]")
    else:
        # Just show the raw topic terms without LLM
        console.print()
        for i, terms in enumerate(topic_result.topics):
            term_text = ", ".join(f"{t} ({w:.3f})" for t, w in terms)
            console.print(f"[bold]Topic {i + 1}[/bold]: {term_text}")


# ------------------------------------------------------------------
# ai summarize
# ------------------------------------------------------------------


@app.command(name="summarize")
def summarize(
    max_records: int = typer.Option(
        100, "--max-records", "-n", help="限制处理的文献数（控制 token 消耗）"
    ),
    language: str = typer.Option(
        "auto", "--language", "-l", help="输出语言: zh, en, auto"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="预览将发送给 LLM 的内容"
    ),
) -> None:
    """LLM 生成文献集合综述摘要（200-500 字）。"""
    records = _get_records()
    if not records:
        return

    client = _get_client(dry_run=dry_run)
    if client is None:
        return

    total_records = len(records)
    if max_records > 0 and max_records < total_records:
        records = records[:max_records]
        console.print(f"[dim]限制为前 {max_records} 篇文献（共 {total_records} 篇）[/dim]")

    lang_hint = ""
    if language == "zh":
        lang_hint = " Please write the summary in Chinese (中文)."
    elif language == "en":
        lang_hint = " Please write the summary in English."

    prompt = (
        f"You are given {len(records)} academic papers (titles and abstracts). "
        "Please generate a comprehensive literature review summary (200-500 words) "
        "covering: (1) main research themes, (2) key methods used, "
        "(3) significant findings, and (4) research gaps or future directions."
        + lang_hint
    )

    console.print("[dim]正在调用 DeepSeek API 生成综述…[/dim]")
    response = client.query(prompt, records, dry_run=dry_run)

    if dry_run:
        console.print("[yellow]🔍 Dry-run 模式 — 将发送以下数据:[/yellow]")
        preview_data = response.content
        console.print_json(preview_data)
        return

    if response.cached:
        console.print("[dim](结果来自缓存)[/dim]")

    console.print()
    console.print(
        Panel(
            response.content,
            title="📄 LLM 文献综述",
            border_style="cyan",
        )
    )
    console.print(f"[dim]Token 消耗: {response.tokens_used}[/dim]")


# ------------------------------------------------------------------
# ai trends
# ------------------------------------------------------------------


@app.command(name="trends")
def trends(
    window: int = typer.Option(
        5, "--window", "-w", help="时间窗口（年）用于对比分析"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="预览将发送给 LLM 的内容"
    ),
) -> None:
    """LLM 识别研究趋势变化、新兴方向和研究空白。"""
    records = _get_records()
    if not records:
        return

    client = _get_client(dry_run=dry_run)
    if client is None:
        return

    # Build year-grouped summary
    year_groups: dict[int, list[str]] = {}
    for r in records:
        if r.year is None:
            continue
        year_groups.setdefault(r.year, []).append(
            f"{r.title}. {r.abstract or ''}"[:200]
        )

    if not year_groups:
        console.print("[yellow]无年份数据[/yellow]")
        return

    years = sorted(year_groups)
    if len(years) < 2:
        console.print("[yellow]年份数据不足以进行趋势分析[/yellow]")
        return

    # Build early vs late comparison
    midpoint = years[len(years) // 2]
    early_years = [y for y in years if y <= midpoint]
    late_years = [y for y in years if y > midpoint]

    early_summary = "\n".join(
        f"({y}) {title}"
        for y in early_years
        for title in year_groups[y][:10]
    )
    late_summary = "\n".join(
        f"({y}) {title}"
        for y in late_years
        for title in year_groups[y][:10]
    )

    early_count = sum(len(year_groups[y]) for y in early_years)
    late_count = sum(len(year_groups[y]) for y in late_years)
    prompt = (
        "Analyze research trends in this academic literature collection.\n\n"
        f"EARLY PERIOD ({min(early_years)}-{max(early_years)}, {early_count} papers):\n"
        f"{early_summary[:3000]}\n\n"
        f"RECENT PERIOD ({min(late_years)}-{max(late_years)}, {late_count} papers):\n"
        f"{late_summary[:3000]}\n\n"
        "Please identify: (1) Shifting research focuses from early to recent, "
        "(2) Emerging hot topics in recent years, (3) Declining research areas, "
        "(4) Potential research gaps and future directions.\n"
        "Structure your response with clear headings."
    )

    console.print("[dim]正在调用 DeepSeek API 分析趋势…[/dim]")
    response = client.query(prompt, records[:100], dry_run=dry_run)

    if dry_run:
        console.print("[yellow]🔍 Dry-run 模式 — 将发送以下数据:[/yellow]")
        console.print_json(response.content)
        return

    if response.cached:
        console.print("[dim](结果来自缓存)[/dim]")

    console.print()
    console.print(
        Panel(
            response.content,
            title="📈 LLM 趋势分析",
            border_style="cyan",
        )
    )
    console.print(f"[dim]Token 消耗: {response.tokens_used}[/dim]")


# ------------------------------------------------------------------
# ai classify
# ------------------------------------------------------------------


@app.command(name="classify")
def classify(
    dimensions: str = typer.Option(
        "methods,theories,applications",
        "--dimensions", "-d",
        help="分类维度（逗号分隔）",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="预览将发送给 LLM 的内容"
    ),
) -> None:
    """LLM 对文献进行多维分类（研究方法、理论框架、应用领域等）。"""
    records = _get_records()
    if not records:
        return

    client = _get_client(dry_run=dry_run)
    if client is None:
        return

    dim_list = [d.strip() for d in dimensions.split(",") if d.strip()]
    dim_desc = ", ".join(dim_list)

    # Batch if many records (limit to 30 per call for quality)
    batch_size = 30
    batch = records[:batch_size]

    prompt = (
        f"Classify the following {len(batch)} academic papers across these dimensions: "
        f"{dim_desc}.\n\n"
        "For each paper, provide classification labels. "
        "Return the result as a structured list.\n"
        "After classifying all papers, provide a summary distribution "
        "for each dimension (e.g. what % of papers use each method)."
    )

    console.print(
        f"[dim]对 {len(batch)} 篇文献按 {dim_desc} 维度进行分类…[/dim]"
    )
    response = client.query(prompt, batch, dry_run=dry_run)

    if dry_run:
        console.print("[yellow]🔍 Dry-run 模式 — 将发送以下数据:[/yellow]")
        console.print_json(response.content)
        return

    if response.cached:
        console.print("[dim](结果来自缓存)[/dim]")

    console.print()
    console.print(
        Panel(
            response.content,
            title=f"🏷 LLM 多维分类 ({dim_desc})",
            border_style="cyan",
        )
    )
    console.print(f"[dim]Token 消耗: {response.tokens_used}[/dim]")


# ------------------------------------------------------------------
# ai info
# ------------------------------------------------------------------


@app.command(name="info")
def info() -> None:
    """显示 LLM 配置状态和缓存统计。"""
    cfg = load_llm_config()
    api_key = cfg["api_key"]
    masked_key = (
        api_key[:8] + "…" + api_key[-4:] if len(api_key) > 12 else api_key
    ) if api_key else ""

    table = Table(
        title="🤖 LLM 配置",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("项目")
    table.add_column("值")
    table.add_column("来源")

    env_key = (
        os.environ.get("CITATIONER_LLM_API_KEY", "")
        or os.environ.get("DEEPSEEK_API_KEY", "")
    )

    if api_key:
        table.add_row("API Key", f"[green]{masked_key}[/green]", _source_label(env_key))
    else:
        table.add_row("API Key", "[red]未配置[/red]", _source_label(env_key))

    for label, cfg_key, env_name in [
        ("模型", "model", "CITATIONER_LLM_MODEL"),
        ("端点", "base_url", "CITATIONER_LLM_BASE_URL"),
        ("Temperature", "temperature", "CITATIONER_LLM_TEMPERATURE"),
        ("Max Tokens", "max_tokens", "CITATIONER_LLM_MAX_TOKENS"),
    ]:
        env_val = os.environ.get(env_name, "")
        table.add_row(label, str(cfg[cfg_key]), _source_label(env_val))

    # Cache stats
    db_path = get_db_path()
    if db_path.exists():
        client = LLMClient(LLMConfig(api_key=""))
        try:
            stats = client.get_cache_stats()
            table.add_row("缓存条目", str(stats["cached_entries"]), "")
            table.add_row("已消耗 Token", f"{stats['total_tokens_used']:,}", "")
        except Exception:
            pass

    console.print(table)

    console.print()
    if not api_key:
        console.print(
            "[yellow]💡 配置 API Key:[/yellow] "
            "[bold]citationer config set llm.api_key <your-key>[/bold]"
        )
    console.print(
        "[dim]管理全部配置: [/dim]"
        "[bold]citationer config show[/bold]"
    )
