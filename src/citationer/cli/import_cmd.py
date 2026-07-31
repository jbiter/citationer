"""Import command — parse and store bibliographic data."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from citationer.cli.scan_cmd import get_registry
from citationer.utils.config import get_db_path
from citationer.utils.database import CitationDatabase
from citationer.utils.serialization import record_to_db_serializable

console = Console()


def _validate_format(value: str) -> str:
    allowed = {"table", "json"}
    if value not in allowed:
        raise typer.BadParameter(f"格式必须是 {allowed} 之一")
    return value


# Keep in sync with scan_cmd.scan supported extensions.
_SUPPORTED_EXTS = {
    ".xlsx",
    ".xls",
    ".txt",
    ".ciw",
    ".csv",
    ".bib",
    ".ris",
    ".xml",
    ".nbib",
    ".rdf",
}


def import_data(
    files: list[Path] | None = typer.Argument(
        None,
        help="要导入的题录文件路径（可多个）。留空则导入当前目录下所有检测到的文件。",
    ),
    keep: bool = typer.Option(
        False,
        "--keep",
        "-k",
        help="保留已有数据，新数据追加到数据库中",
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        help="输出格式: table, json",
        callback=_validate_format,
    ),
) -> None:
    """导入题录文件到本地数据库。默认清除已有数据后重新导入。"""
    registry = get_registry()

    # Auto-detect files if none specified
    file_list: list[Path] = list(files) if files else []
    if not file_list:
        cwd = Path.cwd()
        for ext in _SUPPORTED_EXTS:
            file_list.extend(cwd.glob(f"*{ext}"))
        file_list = sorted(set(file_list))

    if not file_list:
        console.print("[yellow]⚠ 未找到可导入的文件[/yellow]")
        return

    db = CitationDatabase(get_db_path())
    try:
        db.initialize()

        # Always clear existing data unless --keep is set
        if not keep:
            existing = db.get_record_count()
            if existing > 0:
                db.clear_records()
                console.print(f"[yellow]🔄 已清空 {existing} 条已有数据[/yellow]")

        total_records = 0
        parse_errors: list[str] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for filepath in file_list:
                task_id = progress.add_task(
                    f"正在解析 {filepath.name}...", total=None
                )

                parser = registry.find_parser(filepath)
                if parser is None:
                    progress.remove_task(task_id)
                    parse_errors.append(f"{filepath.name}: 无法识别的格式")
                    continue

                try:
                    records = parser.parse(filepath)
                    progress.remove_task(task_id)

                    # Insert per-file with batched commits (every 500 records).
                    # This avoids holding all records in memory AND eliminates
                    # per-record COMMIT overhead.
                    for i, record in enumerate(records):
                        data = record_to_db_serializable(record)
                        db.insert_record(**data, _commit=((i + 1) % 500 == 0))
                    db.conn.commit()  # final flush

                    total_records += len(records)
                    console.print(
                        f"  ✅ {filepath.name} → [green]{len(records)} 条[/green] "
                        f"({parser.source_name})"
                    )
                except Exception as e:
                    progress.remove_task(task_id)
                    parse_errors.append(f"{filepath.name}: {e}")
                    console.print(f"  ❌ {filepath.name} → [red]解析失败: {e}[/red]")
    finally:
        db.close()

    # Summary
    console.print()
    console.print(
        f"📥 导入完成: [bold green]{total_records}[/bold green] 条记录 "
        f"来自 [bold]{len(file_list)}[/bold] 个文件"
    )

    if parse_errors:
        console.print()
        console.print("[yellow]⚠ 解析警告:[/yellow]")
        for err in parse_errors:
            console.print(f"  - {err}")

    if output_format == "json":
        summary = {
            "total_records": total_records,
            "files_processed": len(file_list),
            "errors": parse_errors,
        }
        console.print_json(data=summary)
