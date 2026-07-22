"""Clean command — validate and deduplicate records."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table

from citationer.analysis.dedup import DedupEngine
from citationer.utils.config import get_db_path
from citationer.utils.database import CitationDatabase
from citationer.utils.db_loader import load_records_from_db
from citationer.utils.serialization import record_to_db_serializable

console = Console()


def clean(
    check_duplicates: bool = typer.Option(
        True,
        "--check-duplicates/--no-check-duplicates",
        help="检测并合并重复记录",
    ),
    check_missing: bool = typer.Option(
        True,
        "--check-missing/--no-check-missing",
        help="检测缺失关键字段的记录",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="仅检测，不执行合并",
    ),
    clear_cache: bool = typer.Option(
        False,
        "--cache",
        help="清空数据库缓存文件（.citationer/cache.db）",
    ),
    save: bool = typer.Option(
        False,
        "--save",
        help="保存清洗后的数据为 CSV 文件，方便下次直接导入",
    ),
) -> None:
    """数据清洗：去重、缺失字段检测、异常值检测。"""
    db_path = get_db_path()

    if clear_cache:
        if db_path.exists():
            size = db_path.stat().st_size
            db_path.unlink()
            # Also clean WAL files
            for ext in ("-shm", "-wal"):
                p = db_path.with_suffix(db_path.suffix + ext)
                if p.exists():
                    p.unlink()
            console.print(
                f"[green]✅ 已清空缓存 (释放 {size / 1024 / 1024:.1f} MB)[/green]"
            )
        else:
            console.print("[dim]缓存文件不存在，无需清理[/dim]")
        return

    if not db_path.exists():
        console.print("[yellow]⚠ 尚未导入数据，请先运行 citationer import[/yellow]")
        return

    records = load_records_from_db(db_path)
    if not records:
        console.print("[yellow]⚠ 数据库中没有记录[/yellow]")
        return

    initial_count = len(records)
    issues: list[dict] = []

    # --- Check missing fields ---
    if check_missing:
        missing_table = Table(
            title="🔍 缺失字段检测",
            show_header=True,
            header_style="bold yellow",
        )
        missing_table.add_column("问题类型")
        missing_table.add_column("数量")
        missing_table.add_column("占比")

        missing_title = sum(1 for r in records if not r.title)
        missing_year = sum(1 for r in records if r.year is None)
        missing_authors = sum(1 for r in records if not r.authors)

        for label, count in [
            ("缺少标题", missing_title),
            ("缺少年份", missing_year),
            ("缺少作者", missing_authors),
        ]:
            pct = f"{count / initial_count * 100:.1f}%" if initial_count else "0%"
            style = "red" if count > 0 else "green"
            missing_table.add_row(label, f"[{style}]{count}[/{style}]", pct)

        console.print(missing_table)

        if missing_title > 0:
            issues.append({"type": "missing_title", "count": missing_title})
        if missing_year > 0:
            issues.append({"type": "missing_year", "count": missing_year})
        if missing_authors > 0:
            issues.append({"type": "missing_authors", "count": missing_authors})

    # --- Year anomaly detection ---
    year_anomalies: list[str] = []
    for r in records:
        if r.year is not None and (r.year < 1900 or r.year > 2030):
            year_anomalies.append(f"{r.title[:50]}... → {r.year}")

    if year_anomalies:
        console.print()
        console.print(f"[yellow]⚠ 年份异常检测: {len(year_anomalies)} 条[/yellow]")
        for a in year_anomalies[:5]:
            console.print(f"  - {a}")
        if len(year_anomalies) > 5:
            console.print(f"  ... 还有 {len(year_anomalies) - 5} 条")

    # --- Deduplication ---
    dup_removed = 0
    if check_duplicates:
        console.print()
        engine = DedupEngine()

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task_id = progress.add_task("[cyan]正在执行去重", total=100)

            def _on_layer(step: int, _total: int) -> None:
                progress.update(task_id, completed=step)

            merged, merge_log = engine.deduplicate(records, progress_callback=_on_layer)

        dup_removed = initial_count - len(merged)

        if dup_removed > 0:
            dup_table = Table(
                title="🔗 去重结果",
                show_header=True,
                header_style="bold cyan",
            )
            dup_table.add_column("层级", justify="center")
            dup_table.add_column("类型")
            dup_table.add_column("数量", justify="right")

            layer_counts: dict[int, int] = {}
            for entry in merge_log:
                layer = entry["layer"]
                layer_counts[layer] = layer_counts.get(layer, 0) + 1

            layer_names = {
                1: "DOI 精确匹配",
                2: "标题模糊 (≥85%) + 年份",
                3: "标题模糊 (≥70%) + 第一作者 + 年份",
                4: "跨语言匹配 (中英文)",
            }

            for layer, name in layer_names.items():
                count = layer_counts.get(layer, 0)
                if count > 0:
                    dup_table.add_row(f"Layer {layer}", name, str(count))

            dup_table.add_row(
                "", "[bold]总计[/bold]", f"[bold green]{dup_removed}[/bold green]"
            )
            console.print(dup_table)

            if dry_run:
                console.print()
                console.print(
                    "[yellow]🔍 Dry-run 模式: 未执行合并。"
                    "运行 `citationer clean` 执行合并。[/yellow]"
                )
            else:
                _save_merged_records(db_path, merged)

                console.print()
                console.print(
                    f"✅ 去重完成: [bold red]{initial_count}[/bold red] → "
                    f"[bold green]{len(merged)}[/bold green] 条 "
                    f"(移除 {dup_removed} 条重复)"
                )
        else:
            console.print("[green]✅ 未发现重复记录[/green]")

        # Export cleaned data if --save (BUG-013 fix: independent of
        # whether duplicates were found — the user may want the file even
        # when no dups were detected).
        if save:
            saved_path = _export_csv(merged, Path.cwd())
            console.print(
                f"[green]💾 清洗后数据已保存: {saved_path}[/green]"
            )

    if not issues and dup_removed == 0:
        console.print()
        console.print("[green]✅ 数据质量检查通过，未发现问题[/green]")


def _export_csv(records, base_dir) -> str:
    """Export cleaned records as CSV for reuse. Saves to output/cls/."""
    import csv
    cls_dir = base_dir / "output" / "cls"
    cls_dir.mkdir(parents=True, exist_ok=True)
    out_path = cls_dir / "cleaned_records.csv"
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["title", "authors", "year", "journal", "doi", "abstract"])
        for r in records:
            writer.writerow([
                r.title,
                "; ".join(a.full_name for a in r.authors),
                r.year or "",
                r.journal or "",
                r.doi or "",
                (r.abstract or "")[:200],
            ])
    return str(out_path)


def _save_merged_records(db_path, merged) -> None:
    """Save merged records back to the database."""
    db = CitationDatabase(Path(db_path))
    db.initialize()
    db.clear_records()
    for i, record in enumerate(merged):
        data = record_to_db_serializable(record)
        db.insert_record(**data, _commit=((i + 1) % 500 == 0))
    db.conn.commit()  # final flush
    db.close()
