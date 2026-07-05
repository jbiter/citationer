"""Network analysis CLI commands — co-occurrence, collaboration, citation."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from citationer.analysis.network import NetworkEngine
from citationer.utils.db_loader import get_records

app = typer.Typer(
    name="network",
    help="知识图谱与网络分析",
    no_args_is_help=True,
)

console = Console()


_get_records = get_records


def _get_output_path(
    output: Path | None, default_name: str, fmt: str
) -> Path:
    """Resolve the output file path."""
    if output:
        return output
    return Path.cwd() / f"{default_name}.{fmt}"


# ------------------------------------------------------------------
# network keywords
# ------------------------------------------------------------------


@app.command(name="keywords")
def keywords(
    top_n: int = typer.Option(50, "--top", "-n", help="包含 Top-N 高频关键词"),
    threshold: int = typer.Option(
        3, "--threshold", "-t", help="最少共现次数（低于此值不显示边）"
    ),
    output_format: str = typer.Option(
        "table", "--output-format", "-f",
        help="输出格式: table, csv, gexf, graphml",
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="输出文件路径"
    ),
    viz: bool = typer.Option(
        False, "--viz/--no-viz", help="生成 HTML 交互式网络图"
    ),
) -> None:
    """关键词共现网络分析。"""
    records = _get_records()
    if not records:
        return

    engine = NetworkEngine(records)
    result = engine.keyword_cooccurrence(top_n=top_n, threshold=threshold)

    if not result.edges:
        console.print(
            "[yellow]未找到满足条件的共现关系，"
            "请降低 --threshold 或减少 --top[/yellow]"
        )
        return

    if output_format == "table":
        console.print()
        table = Table(
            title=f"🔗 关键词共现网络 (Top-{result.total_keywords}, "
                  f"{result.total_edges} 条边, threshold≥{threshold})",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("#", justify="right", style="dim")
        table.add_column("关键词 A")
        table.add_column("关键词 B")
        table.add_column("共现次数", justify="right")

        for i, (a, b, w) in enumerate(result.edges[:30], 1):
            table.add_row(str(i), a, b, str(w))

        console.print(table)
        if result.total_edges > 30:
            console.print(f"[dim]... 还有 {result.total_edges - 30} 条边[/dim]")

    elif output_format == "csv":
        out_path = _get_output_path(output, "keyword_cooccurrence", "csv")
        NetworkEngine.to_csv(result.edges, out_path)
        console.print(f"[green]CSV 已保存到 {out_path}[/green]")

    elif output_format == "gexf":
        out_path = _get_output_path(output, "keyword_cooccurrence", "gexf")
        nodes = [(kw, 1) for kw in result.keywords]
        NetworkEngine.to_gexf(result.edges, nodes, out_path)
        console.print(f"[green]GEXF 已保存到 {out_path}[/green]")

    elif output_format == "graphml":
        out_path = _get_output_path(output, "keyword_cooccurrence", "graphml")
        nodes = [(kw, 1) for kw in result.keywords]
        NetworkEngine.to_graphml(result.edges, nodes, out_path)
        console.print(f"[green]GraphML 已保存到 {out_path}[/green]")

    # HTML visualization
    if viz:
        vis_path = _get_output_path(output, "keyword_network", "html")
        nodes = [(kw, 1) for kw in result.keywords]
        NetworkEngine.to_html(result.edges, nodes, None, vis_path, "关键词共现网络")
        console.print(f"[green]HTML 交互图已保存到 {vis_path}[/green]")


# ------------------------------------------------------------------
# network coauthors
# ------------------------------------------------------------------


@app.command(name="coauthors")
def coauthors(
    min_papers: int = typer.Option(
        2, "--min-papers", "-m", help="最少发文数（低于此值的作者不显示）"
    ),
    collab_type: str = typer.Option(
        "authors", "--type", "-t", help="网络类型: authors, institutions"
    ),
    output_format: str = typer.Option(
        "table", "--output-format", "-f",
        help="输出格式: table, csv, gexf, graphml",
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="输出文件路径"
    ),
    viz: bool = typer.Option(
        False, "--viz/--no-viz", help="生成 HTML 交互式网络图"
    )
) -> None:
    """作者/机构合作网络分析。"""
    records = _get_records()
    if not records:
        return

    engine = NetworkEngine(records)
    result = engine.author_collaboration(
        min_papers=min_papers, collab_type=collab_type
    )

    if not result.edges:
        console.print(
            "[yellow]未找到满足条件的合作关系，请降低 --min-papers[/yellow]"
        )
        return

    label = "作者" if collab_type == "authors" else "机构"

    if output_format == "table":
        console.print()
        # Top collaborators
        table = Table(
            title=f"🤝 {label}合作网络 "
                  f"({result.total_nodes} 个{label}, {result.total_edges} 条边)",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("#", justify="right", style="dim")
        table.add_column(f"{label} A")
        table.add_column(f"{label} B")
        table.add_column("合作次数", justify="right")

        for i, (a, b, w) in enumerate(result.edges[:20], 1):
            table.add_row(str(i), a, b, str(w))

        console.print(table)

        # Communities
        if result.communities:
            community_count = len(set(result.communities.values()))
            console.print(f"[dim]检测到 {community_count} 个社区 (Louvain 算法)[/dim]")

    elif output_format == "csv":
        out_path = _get_output_path(output, f"{collab_type}_collaboration", "csv")
        NetworkEngine.to_csv(result.edges, out_path)
        console.print(f"[green]CSV 已保存到 {out_path}[/green]")

    elif output_format == "gexf":
        out_path = _get_output_path(output, f"{collab_type}_collaboration", "gexf")
        NetworkEngine.to_gexf(result.edges, result.nodes, out_path)
        console.print(f"[green]GEXF 已保存到 {out_path}[/green]")

    elif output_format == "graphml":
        out_path = _get_output_path(output, f"{collab_type}_collaboration", "graphml")
        NetworkEngine.to_graphml(result.edges, result.nodes, out_path)
        console.print(f"[green]GraphML 已保存到 {out_path}[/green]")

    if viz:
        vis_path = _get_output_path(output, f"{collab_type}_network", "html")
        NetworkEngine.to_html(
            result.edges, result.nodes, result.communities,
            vis_path, f"{label}合作网络",
        )
        console.print(f"[green]HTML 交互图已保存到 {vis_path}[/green]")


# ------------------------------------------------------------------
# network cocitation
# ------------------------------------------------------------------


@app.command(name="cocitation")
def cocitation(
    top_n: int = typer.Option(30, "--top", "-n", help="显示 Top-N 共被引对"),
    output_format: str = typer.Option(
        "table", "--output-format", "-f",
        help="输出格式: table, csv, gexf, graphml",
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="输出文件路径"
    ),
    viz: bool = typer.Option(
        False, "--viz/--no-viz", help="生成 HTML 交互式网络图"
    )
) -> None:
    """共被引分析：两篇文献同时被第三篇引用。"""
    records = _get_records()
    if not records:
        return

    engine = NetworkEngine(records)
    result = engine.co_citation(top_n=top_n)

    if not result.edges:
        console.print(
            "[yellow]未找到共被引关系。"
            "注意：共被引分析需要题录中包含参考文献数据（WoS 导出通常包含，CNKI 不包含）[/yellow]"
        )
        return

    if output_format == "table":
        console.print()
        table = Table(
            title=f"📚 共被引分析 (Top-{result.total_edges})",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("#", justify="right", style="dim")
        table.add_column("文献 A")
        table.add_column("文献 B")
        table.add_column("共被引次数", justify="right")

        for i, (a, b, w) in enumerate(result.edges[:20], 1):
            a_short = a[:60] + "…" if len(a) > 60 else a
            b_short = b[:60] + "…" if len(b) > 60 else b
            table.add_row(str(i), a_short, b_short, str(w))

        console.print(table)

    elif output_format == "csv":
        out_path = _get_output_path(output, "cocitation", "csv")
        NetworkEngine.to_csv(result.edges, out_path)
        console.print(f"[green]CSV 已保存到 {out_path}[/green]")

    elif output_format in ("gexf", "graphml"):
        out_path = _get_output_path(output, "cocitation", output_format)
        if output_format == "gexf":
            NetworkEngine.to_gexf(result.edges, None, out_path)
        else:
            NetworkEngine.to_graphml(result.edges, None, out_path)
        console.print(f"[green]{output_format.upper()} 已保存到 {out_path}[/green]")

    if viz:
        vis_path = _get_output_path(output, "cocitation_network", "html")
        NetworkEngine.to_html(
            result.edges, None, None, vis_path, "共被引网络",
        )
        console.print(f"[green]HTML 交互图已保存到 {vis_path}[/green]")


# ------------------------------------------------------------------
# network coupling
# ------------------------------------------------------------------


@app.command(name="coupling")
def coupling(
    top_n: int = typer.Option(30, "--top", "-n", help="显示 Top-N 耦合对"),
    output_format: str = typer.Option(
        "table", "--output-format", "-f",
        help="输出格式: table, csv, gexf, graphml",
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="输出文件路径"
    ),
    viz: bool = typer.Option(
        False, "--viz/--no-viz", help="生成 HTML 交互式网络图"
    )
) -> None:
    """文献耦合分析：两篇文献有共同参考文献。"""
    records = _get_records()
    if not records:
        return

    engine = NetworkEngine(records)
    result = engine.bibliographic_coupling(top_n=top_n)

    if not result.edges:
        console.print("[yellow]未找到文献耦合关系[/yellow]")
        return

    type_label = {
        "bibliographic_coupling": "参考文献耦合",
        "keyword_coupling": "关键词耦合 (参考文献数据不可用时的降级方案)",
    }.get(result.graph_type, result.graph_type)

    if output_format == "table":
        console.print()
        table = Table(
            title=f"📖 文献耦合分析 ({type_label}, Top-{result.total_edges})",
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("#", justify="right", style="dim")
        table.add_column("文献 A")
        table.add_column("文献 B")
        table.add_column("耦合强度", justify="right")

        for i, (a, b, w) in enumerate(result.edges[:20], 1):
            a_short = a[:50] + "…" if len(a) > 50 else a
            b_short = b[:50] + "…" if len(b) > 50 else b
            table.add_row(str(i), a_short, b_short, str(w))

        console.print(table)

    elif output_format == "csv":
        out_path = _get_output_path(output, "bibliographic_coupling", "csv")
        NetworkEngine.to_csv(result.edges, out_path)
        console.print(f"[green]CSV 已保存到 {out_path}[/green]")

    elif output_format in ("gexf", "graphml"):
        out_path = _get_output_path(output, "bibliographic_coupling", output_format)
        if output_format == "gexf":
            NetworkEngine.to_gexf(result.edges, None, out_path)
        else:
            NetworkEngine.to_graphml(result.edges, None, out_path)
        console.print(f"[green]{output_format.upper()} 已保存到 {out_path}[/green]")

    if viz:
        vis_path = _get_output_path(output, "coupling_network", "html")
        NetworkEngine.to_html(
            result.edges, None, None, vis_path, "文献耦合网络",
        )
        console.print(f"[green]HTML 交互图已保存到 {vis_path}[/green]")
