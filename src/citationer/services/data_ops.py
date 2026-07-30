"""数据操作服务层，隔离 Web API 与 CLI 命令的具体实现。"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
from typing import Any

from citationer.utils.database import CitationDatabase


def get_record_count(db: CitationDatabase) -> int:
    """通过已初始化的数据库对象高效获取记录总数。"""
    return db.get_record_count()


def _run_isolated(func: Any, *args: Any, **kwargs: Any) -> None:
    """运行 CLI 命令函数，捕获 stdout/stderr 并转换退出异常。"""
    import typer

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            func(*args, **kwargs)
    except typer.Exit as exc:
        if exc.exit_code != 0:
            raise RuntimeError(f"CLI 命令失败，退出码 {exc.exit_code}") from exc
    except SystemExit as exc:
        if exc.code not in (0, None):
            raise RuntimeError(f"CLI 命令失败，退出码 {exc.code}") from exc


def run_scan(directory: Path | None = None, recursive: bool = True) -> None:
    """扫描目录下的题录文件（隔离 stdout/stderr 与退出异常）。"""
    from citationer.cli.scan_cmd import scan

    _run_isolated(scan, directory or Path.cwd(), recursive=recursive)


def run_import(files: list[Path] | None = None, keep: bool = False) -> None:
    """导入题录文件到本地数据库（隔离 stdout/stderr 与退出异常）。"""
    from citationer.cli.import_cmd import import_data

    _run_isolated(import_data, files, keep=keep)


def run_clean(
    *,
    check_duplicates: bool = True,
    check_missing: bool = True,
    dry_run: bool = False,
    clear_cache: bool = False,
    save: bool = False,
    non_interactive: bool = True,
) -> None:
    """执行数据清洗（隔离 stdout/stderr 与退出异常，默认非交互）。"""
    from citationer.cli.clean_cmd import clean

    _run_isolated(
        clean,
        check_duplicates=check_duplicates,
        check_missing=check_missing,
        dry_run=dry_run,
        clear_cache=clear_cache,
        save=save,
        non_interactive=non_interactive,
    )
