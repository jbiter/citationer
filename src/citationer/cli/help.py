"""Custom Rich-formatted help renderer for citationer L1 overview."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

import citationer

VERSION = citationer.__version__

# ── colour palette ──────────────────────────────────────────────
SECTION_STYLE = "bold bright_cyan"
HEADER_STYLE = "bold yellow"
CMD_STYLE = "bold green"
OPT_STYLE = "dim cyan"
DESC_STYLE = "white"
HINT_STYLE = "dim"

# ── command registry ────────────────────────────────────────────

_TOP_LEVEL: list[tuple[str, str]] = [
    ("scan", "扫描目录下的题录文件，自动识别格式和来源"),
    ("status", "快速查看当前目录状态（简化版 scan）"),
    ("import", "导入题录文件到本地 SQLite 数据库"),
    ("clean", "数据清洗：缺失字段检测、异常值检测、智能去重"),
]

_GROUPS: list[tuple[str, str, list[tuple[str, str]]]] = [
    ("stats", "描述性统计分析", [
        ("overview", "文献全景概览"),
        ("yearly", "年度发表趋势"),
        ("journals", "期刊/来源分析"),
        ("authors", "作者分析"),
        ("institutions", "机构分析"),
        ("citations", "引用分析"),
    ]),
    ("text", "文本挖掘与 NLP", [
        ("preprocess", "分词 + 语言检测"),
        ("keywords", "关键词频次统计"),
        ("topics", "LDA/NMF 主题建模"),
        ("summarize", "TF-IDF 关键句提取"),
        ("cluster", "K-Means / 层次聚类"),
    ]),
    ("network", "知识图谱与网络分析", [
        ("keywords", "关键词共现网络"),
        ("coauthors", "作者/机构合作网络"),
        ("cocitation", "共被引分析"),
        ("coupling", "文献耦合分析"),
    ]),
    ("ai", "LLM 驱动的深度语义分析", [
        ("topics", "主题自动标注"),
        ("summarize", "文献综述生成"),
        ("trends", "研究趋势识别"),
        ("classify", "多维分类"),
        ("info", "配置状态查看"),
        ("key-papers", "关键文献识别"),
    ]),
    ("trend", "研究趋势分析", [
        ("hotspots", "关键词突变检测"),
        ("strategy", "战略坐标图"),
        ("river", "主题河流图"),
    ]),
    ("report", "报告生成", [
        ("quick", "快速生成报告"),
        ("custom", "自定义报告"),
    ]),
    ("export", "数据导出", [
        ("csv", "导出 CSV"),
        ("json", "导出 JSON"),
        ("bibtex", "导出 BibTeX"),
    ]),
]

_TOOLS: list[tuple[str, str]] = [
    ("config", "管理 LLM 和其他配置项 (show / set / init)"),
]


def render_l1_overview() -> None:
    """Render the L1 overview help screen."""
    console = Console()

    _header(console)
    _quickstart(console)
    _section(console, "📁 数据管理", _TOP_LEVEL)
    _section_groups(console)
    _section(console, "🔧 工具与配置", _TOOLS)
    _global_options(console)
    _footer(console)


def _header(console: Console) -> None:
    console.print()
    console.print(
        Panel(
            Text("citationer —— 文献题录分析 CLI 工具", style="bold white"),
            border_style="cyan",
        )
    )
    console.print(f"  [dim]version {VERSION}[/dim]")
    console.print()


def _quickstart(console: Console) -> None:
    console.print(f"  [{HEADER_STYLE}]快速开始[/{HEADER_STYLE}]")
    console.print(f"    [{CMD_STYLE}]$[/{CMD_STYLE}] cd /path/to/literature")
    console.print(
        f"    [{CMD_STYLE}]$[/{CMD_STYLE}] citationer "
        f"[{OPT_STYLE}]scan[/{OPT_STYLE}]           "
        f"[{HINT_STYLE}]# 扫描题录文件[/{HINT_STYLE}]"
    )
    console.print(
        f"    [{CMD_STYLE}]$[/{CMD_STYLE}] citationer "
        f"[{OPT_STYLE}]import[/{OPT_STYLE}]         "
        f"[{HINT_STYLE}]# 导入数据[/{HINT_STYLE}]"
    )
    console.print(
        f"    [{CMD_STYLE}]$[/{CMD_STYLE}] citationer "
        f"[{OPT_STYLE}]stats overview[/{OPT_STYLE}] "
        f"[{HINT_STYLE}]# 查看概览[/{HINT_STYLE}]"
    )
    console.print()


def _section(
    console: Console, title: str, commands: list[tuple[str, str]]
) -> None:
    console.print(f"  [{SECTION_STYLE}]{title}[/{SECTION_STYLE}]")
    for name, desc in commands:
        console.print(
            f"    [{CMD_STYLE}]{name:<14}[/{CMD_STYLE}]"
            f"[{DESC_STYLE}]{desc}[/{DESC_STYLE}]"
        )
    console.print()


def _section_groups(console: Console) -> None:
    console.print(f"  [{SECTION_STYLE}]📊 分析引擎[/{SECTION_STYLE}]")
    for group_name, group_desc, subcmds in _GROUPS:
        sub_list = ", ".join(c[0] for c in subcmds)
        console.print(
            f"    [{CMD_STYLE}]{group_name:<14}[/{CMD_STYLE}]"
            f"[{DESC_STYLE}]{group_desc}[/{DESC_STYLE}]"
        )
        console.print(
            f"                    [{HINT_STYLE}]({sub_list})[/{HINT_STYLE}]"
        )
    console.print()


def _global_options(console: Console) -> None:
    console.print(f"  [{SECTION_STYLE}]🌐 全局选项[/{SECTION_STYLE}]")
    opts = [
        ("--verbose, -v", "详细输出（调试模式）"),
        ("--quiet, -q", "安静模式（仅输出结果数据）"),
        ("--output, -o PATH", "指定输出目录"),
        ("--no-color", "禁用彩色输出"),
        ("--help, -h", "显示帮助信息"),
    ]
    for flag, desc in opts:
        console.print(
            f"    [{OPT_STYLE}]{flag:<20}[/{OPT_STYLE}]"
            f"[{DESC_STYLE}]{desc}[/{DESC_STYLE}]"
        )
    console.print()


def _footer(console: Console) -> None:
    console.print()
    console.print(
        f"  [{HINT_STYLE}]使用 "
        f"[{CMD_STYLE}]citationer <command> --help[/{CMD_STYLE}] "
        f"查看子命令详情[/{HINT_STYLE}]"
    )
    console.print(
        f"  [{HINT_STYLE}]使用 "
        f"[{CMD_STYLE}]citationer <group> <subcommand> --help[/{CMD_STYLE}] "
        f"查看完整参数说明[/{HINT_STYLE}]"
    )
    console.print()
