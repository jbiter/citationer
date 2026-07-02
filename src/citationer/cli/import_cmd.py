"""Import command — parse and store bibliographic data."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from citationer.cli.scan_cmd import get_registry
from citationer.models.record import Record
from citationer.utils.config import get_db_path
from citationer.utils.database import CitationDatabase

console = Console()


def import_data(
    files: list[Path] | None = typer.Argument(
        None,
        help="要导入的题录文件路径（可多个）。留空则导入当前目录下所有检测到的文件。",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="强制重新导入（清空已有数据）",
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        help="输出格式: table, json",
    ),
) -> None:
    """导入题录文件到本地数据库。"""
    registry = get_registry()
    db = CitationDatabase(get_db_path())
    db.initialize()

    if force:
        db.clear_records()
        console.print("[yellow]🔄 已清空已有数据[/yellow]")

    # Auto-detect files if none specified
    file_list: list[Path] = list(files) if files else []
    if not file_list:
        cwd = Path.cwd()
        supported_exts = {".xlsx", ".xls", ".txt", ".ciw", ".csv"}
        for ext in supported_exts:
            file_list.extend(cwd.glob(f"*{ext}"))
        file_list = sorted(set(file_list))

    if not file_list:
        console.print("[yellow]⚠ 未找到可导入的文件[/yellow]")
        return

    all_records: list[Record] = []
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
                all_records.extend(records)
                progress.remove_task(task_id)
                console.print(
                    f"  ✅ {filepath.name} → [green]{len(records)} 条[/green] "
                    f"({parser.source_name})"
                )
            except Exception as e:
                progress.remove_task(task_id)
                parse_errors.append(f"{filepath.name}: {e}")
                console.print(f"  ❌ {filepath.name} → [red]解析失败: {e}[/red]")

    # Store in database
    if all_records:
        for record in all_records:
            authors_data = [
                {
                    "full_name": a.full_name,
                    "surname": a.surname,
                    "given_name": a.given_name,
                    "order": a.order,
                    "is_corresponding": a.is_corresponding,
                    "affiliation": a.affiliation,
                    "email": a.email,
                }
                for a in record.authors
            ]
            keywords_data = [
                {"keyword": k, "lang": "zh"} for k in record.keywords
            ]
            institutions_data = [
                {
                    "name": i.name,
                    "country": i.country,
                    "province": i.province,
                    "city": i.city,
                    "inst_type": i.inst_type,
                }
                for i in record.institutions
            ]

            db.insert_record(
                record_data={
                    "source_database": record.source_database,
                    "source_file": record.source_file,
                    "title": record.title,
                    "title_en": record.title_en,
                    "year": record.year,
                    "journal": record.journal,
                    "volume": record.volume,
                    "issue": record.issue,
                    "pages": record.pages,
                    "doi": record.doi,
                    "issn": record.issn,
                    "abstract": record.abstract,
                    "abstract_en": record.abstract_en,
                    "doc_type": record.doc_type.value,
                    "language": record.language,
                    "citation_count": record.citation_count,
                    "raw_data": record.raw_data,
                },
                authors=authors_data,
                keywords=keywords_data,
                institutions=institutions_data,
            )

    db.close()

    # Summary
    console.print()
    console.print(
        f"📥 导入完成: [bold green]{len(all_records)}[/bold green] 条记录 "
        f"来自 [bold]{len(file_list)}[/bold] 个文件"
    )

    if parse_errors:
        console.print()
        console.print("[yellow]⚠ 解析警告:[/yellow]")
        for err in parse_errors:
            console.print(f"  - {err}")

    if output_format == "json":
        summary = {
            "total_records": len(all_records),
            "files_processed": len(file_list),
            "errors": parse_errors,
        }
        console.print_json(data=summary)
