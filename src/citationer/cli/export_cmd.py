"""Export command — export bibliographic data in various formats."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import typer
from rich.console import Console

from citationer.utils.config import get_db_path
from citationer.utils.db_loader import load_records_from_db

app = typer.Typer(
    name="export",
    help="数据导出",
    no_args_is_help=True,
)

console = Console()


@app.command(name="csv")
def export_csv(
    output: Path = typer.Option(
        ..., "--output", "-o", help="输出文件路径"
    ),
) -> None:
    """导出为 CSV 格式。"""
    _export("csv", output)


@app.command(name="json")
def export_json(
    output: Path = typer.Option(
        ..., "--output", "-o", help="输出文件路径"
    ),
) -> None:
    """导出为 JSON 格式。"""
    _export("json", output)


@app.command(name="bibtex")
def export_bibtex(
    output: Path = typer.Option(
        ..., "--output", "-o", help="输出文件路径"
    ),
) -> None:
    """导出为 BibTeX 格式。"""
    _export("bibtex", output)


@app.command(name="ris")
def export_ris(
    output: Path = typer.Option(
        ..., "--output", "-o", help="输出文件路径"
    ),
) -> None:
    """导出为 RIS 格式。"""
    _export("ris", output)


@app.command(name="xlsx")
def export_xlsx(
    output: Path = typer.Option(
        ..., "--output", "-o", help="输出文件路径"
    ),
) -> None:
    """导出为 Excel 格式。"""
    _export("xlsx", output)


def _export(fmt: str, output: Path) -> None:
    """Core export logic."""
    db_path = get_db_path()
    if not db_path.exists():
        console.print("[yellow]⚠ 尚未导入数据[/yellow]")
        return

    records = load_records_from_db(db_path)
    if not records:
        console.print("[yellow]⚠ 数据库中没有记录[/yellow]")
        return

    output.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "csv":
        with open(output, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["title", "authors", "year", "journal", "doi", "language", "doc_type"])
            for r in records:
                writer.writerow([
                    r.title,
                    "; ".join(a.full_name for a in r.authors),
                    r.year or "",
                    r.journal or "",
                    r.doi or "",
                    r.language or "",
                    r.doc_type.value,
                ])
    elif fmt == "json":
        data = []
        for r in records:
            data.append({
                "title": r.title,
                "authors": [a.full_name for a in r.authors],
                "year": r.year,
                "journal": r.journal,
                "doi": r.doi,
                "keywords": r.keywords,
                "abstract": r.abstract,
                "language": r.language,
                "doc_type": r.doc_type.value,
                "citation_count": r.citation_count,
            })
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    elif fmt == "bibtex":
        lines = []
        for i, r in enumerate(records):
            key = f"ref{i+1}"
            lines.append(f"@article{{{key},")
            lines.append(f"  title = {{{r.title}}},")
            if r.authors:
                lines.append("  author = {" +
                             " and ".join(a.full_name for a in r.authors) + "},")
            if r.year:
                lines.append(f"  year = {{{r.year}}},")
            if r.journal:
                lines.append(f"  journal = {{{r.journal}}},")
            if r.doi:
                lines.append(f"  doi = {{{r.doi}}},")
            if r.volume:
                lines.append(f"  volume = {{{r.volume}}},")
            if r.issue:
                lines.append(f"  number = {{{r.issue}}},")
            if r.pages:
                lines.append(f"  pages = {{{r.pages}}},")
            lines.append("}")
            lines.append("")
        output.write_text("\n".join(lines), encoding="utf-8")
    elif fmt == "ris":
        lines = []
        for r in records:
            lines.append("TY  - JOUR")
            lines.append(f"TI  - {r.title}")
            for a in r.authors:
                lines.append(f"AU  - {a.full_name}")
            if r.year:
                lines.append(f"PY  - {r.year}")
            if r.journal:
                lines.append(f"JO  - {r.journal}")
            if r.volume:
                lines.append(f"VL  - {r.volume}")
            if r.issue:
                lines.append(f"IS  - {r.issue}")
            if r.pages:
                lines.append(f"SP  - {r.pages}")
            if r.doi:
                lines.append(f"DO  - {r.doi}")
            for kw in r.keywords:
                lines.append(f"KW  - {kw}")
            if r.abstract:
                lines.append(f"AB  - {r.abstract}")
            lines.append("ER  - ")
            lines.append("")
        output.write_text("\n".join(lines), encoding="utf-8")
    elif fmt == "xlsx":
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Title", "Authors", "Year", "Journal", "DOI",
                    "Keywords", "Abstract", "Language"])
        for r in records:
            ws.append([
                r.title,
                "; ".join(a.full_name for a in r.authors),
                r.year or "",
                r.journal or "",
                r.doi or "",
                "; ".join(r.keywords),
                r.abstract or "",
                r.language or "",
            ])
        wb.save(str(output))
        wb.close()

    console.print(f"[green]✅ 已导出 {len(records)} 条记录 → {output}[/green]")
