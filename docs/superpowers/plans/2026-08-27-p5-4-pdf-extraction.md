# P5-4 PDF 文本提取实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Citationer 新增 `citationer pdf extract` 命令，递归提取目录下所有 PDF 的纯文本并输出 JSON。

**Architecture:** 新增 `citationer.pdf` 子包负责 PDF 扫描与文本提取；新增 `citationer.cli.pdf_cmd` 提供 CLI 入口；在 `main.py` 和 `help.py` 注册命令组。核心依赖为 `pypdf`。

**Tech Stack:** Python 3.11+, Typer, Rich, pypdf, pytest.

**Spec:** `docs/superpowers/specs/2026-08-27-p5-4-pdf-extraction-design.md`

## Global Constraints

- Python >= 3.11
- 不直接提交到 `main`，所有工作在当前 `feat/p5.4-pdf-extraction` 分支完成
- `pypdf` 作为可选依赖放在 `text` 和 `all` 组
- 新增代码必须通过 `ruff check src/ tests/`
- 先不跑完整测试套件、不发布（用户后续指令）

---

## File Structure

| 文件 | 类型 | 职责 |
|---|---|---|
| `pyproject.toml` | 修改 | 在 `text` 和 `all` 可选依赖组加入 `pypdf>=4.0` |
| `src/citationer/pdf/__init__.py` | 新建 | `pdf` 子包包初始化 |
| `src/citationer/pdf/extractor.py` | 新建 | `PdfExtractor`：目录扫描、单文件提取、错误处理 |
| `src/citationer/cli/pdf_cmd.py` | 新建 | `citationer pdf extract` 命令 |
| `src/citationer/cli/main.py` | 修改 | 懒加载并注册 `pdf` 命令组 |
| `src/citationer/cli/help.py` | 修改 | 在 L1 Help 的 `_GROUPS` 中加入 `pdf` |
| `tests/test_pdf_extractor.py` | 新建 | `PdfExtractor` 单元测试 |
| `tests/test_pdf_cmd.py` | 新建 | `pdf extract` CLI 测试 |

---

### Task 1: 添加 pypdf 依赖

**Files:**
- Modify: `pyproject.toml:23-27` (`text` 可选依赖组)
- Modify: `pyproject.toml:60-74` (`all` 可选依赖组)

**Interfaces:**
- Consumes: 无
- Produces: `pypdf>=4.0` 出现在 `text` 和 `all` 依赖中

- [ ] **Step 1: 修改 `text` 组**

```toml
text = [
    "jieba>=0.42",
    "gensim>=4.3",
    "scikit-learn>=1.4",
    "pypdf>=4.0",
]
```

- [ ] **Step 2: 在 `all` 组末尾追加 `pypdf`**

```toml
all = [
    "jieba>=0.42",
    "gensim>=4.3",
    "scikit-learn>=1.4",
    "rapidfuzz>=3.0",
    "networkx>=3.2",
    "python-louvain>=0.16",
    "plotly>=5.18",
    "openai>=1.12",
    "wordcloud>=1.9",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "jinja2>=3.1",
    "python-multipart>=0.0.9",
    "pypdf>=4.0",
]
```

- [ ] **Step 3: 提交**

```bash
git add pyproject.toml
git commit -m "build(deps): add pypdf to text and all extras for P5-4"
```

---

### Task 2: 创建 PDF 提取器

**Files:**
- Create: `src/citationer/pdf/__init__.py`
- Create: `src/citationer/pdf/extractor.py`

**Interfaces:**
- Consumes: `pypdf.PdfReader`
- Produces:
  - `PdfExtractor(recursive: bool = True, max_chars: int = 0)`
  - `PdfExtractor.extract_directory(directory: Path) -> dict[str, Any]`
  - `PdfExtractor.extract_file(filepath: Path) -> dict[str, Any]`

- [ ] **Step 1: 创建 `src/citationer/pdf/__init__.py`**

```python
"""PDF full-text extraction utilities."""

from __future__ import annotations

from citationer.pdf.extractor import PdfExtractor

__all__ = ["PdfExtractor"]
```

- [ ] **Step 2: 创建 `src/citationer/pdf/extractor.py`**

```python
"""PDF text extraction engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader


class PdfExtractor:
    """Extract text from a directory of PDF files."""

    def __init__(self, recursive: bool = True, max_chars: int = 0) -> None:
        self.recursive = recursive
        self.max_chars = max_chars

    def extract_directory(self, directory: Path) -> dict[str, Any]:
        """Extract text from all PDF files under *directory*."""
        directory = directory.resolve()
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        pattern = "**/*.pdf" if self.recursive else "*.pdf"
        pdf_files = sorted(directory.glob(pattern))

        files: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for filepath in pdf_files:
            result = self.extract_file(filepath)
            if result["status"] == "success":
                files.append(result)
            else:
                errors.append(result)

        return {
            "files": files,
            "errors": errors,
            "summary": {
                "total": len(files) + len(errors),
                "success": len(files),
                "failed": len(errors),
            },
        }

    def extract_file(self, filepath: Path) -> dict[str, Any]:
        """Extract text from a single PDF file."""
        try:
            reader = PdfReader(str(filepath))
            text_parts: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)

            full_text = "\n".join(text_parts).strip()
            if self.max_chars > 0:
                full_text = full_text[: self.max_chars]

            return {
                "filename": filepath.name,
                "path": str(filepath),
                "page_count": len(reader.pages),
                "word_count": len(full_text.split()),
                "text": full_text,
                "status": "success",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "filename": filepath.name,
                "path": str(filepath),
                "error": str(exc),
                "status": "error",
            }
```

- [ ] **Step 3: 提交**

```bash
git add src/citationer/pdf/
git commit -m "feat(pdf): add PdfExtractor for directory and single-file text extraction"
```

---

### Task 3: 创建 PDF CLI 命令

**Files:**
- Create: `src/citationer/cli/pdf_cmd.py`

**Interfaces:**
- Consumes: `citationer.pdf.extractor.PdfExtractor`
- Produces: `typer.Typer` app named `pdf` with `extract` subcommand

- [ ] **Step 1: 创建 `src/citationer/cli/pdf_cmd.py`**

```python
"""PDF analysis commands."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from citationer.pdf.extractor import PdfExtractor

app = typer.Typer(
    name="pdf",
    help="PDF 全文分析",
    no_args_is_help=True,
)

console = Console()


@app.command(name="extract")
def extract_command(
    directory: Path = typer.Argument(
        ...,
        help="PDF 文件目录",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    output: Path = typer.Option(
        Path("pdf_texts.json"),
        "--output",
        "-o",
        help="输出 JSON 文件",
    ),
    recursive: bool = typer.Option(
        True,
        "--recursive/--no-recursive",
        help="是否递归子目录",
    ),
    max_chars: int = typer.Option(
        0,
        "--max-chars",
        "-m",
        help="单个文件最大字符数（0 为不截断）",
    ),
) -> None:
    """提取一个目录下所有 PDF 的文本内容。"""
    extractor = PdfExtractor(recursive=recursive, max_chars=max_chars)
    result = extractor.extract_directory(directory)

    output_json = json.dumps(result, ensure_ascii=False, indent=2)
    output.write_text(output_json, encoding="utf-8")

    summary = result["summary"]
    console.print(
        f"[green]✓ 处理完成：{summary['success']} 成功，"
        f"{summary['failed']} 失败，共 {summary['total']} 个文件[/green]"
    )
    console.print(f"[dim]结果已保存到 {output}[/dim]")
```

- [ ] **Step 2: 提交**

```bash
git add src/citationer/cli/pdf_cmd.py
git commit -m "feat(cli): add citationer pdf extract command"
```

---

### Task 4: 注册命令组并更新 L1 Help

**Files:**
- Modify: `src/citationer/cli/main.py`
- Modify: `src/citationer/cli/help.py`

**Interfaces:**
- Consumes: `citationer.cli.pdf_cmd.app`
- Produces: `citationer pdf` 命令可用；L1 Help 显示 `pdf` 组

- [ ] **Step 1: 在 `main.py` 添加懒加载函数和注册**

在 `def _import_plugins():` 附近插入：

```python
def _import_pdf():
    from citationer.cli import pdf_cmd
    return pdf_cmd
```

在 `_register()` 中 `app.add_typer(_import_plugins().app, name="plugins")` 之前或之后插入：

```python
    app.add_typer(_import_pdf().app, name="pdf")
```

完整 `_register()` 应类似：

```python
def _register():
    """Register all commands. Called once on first dispatch."""
    if _register._done:
        return
    _register._done = True

    scan = _import_scan()
    imp = _import_import()
    clean = _import_clean()
    app.command(name="scan")(scan.scan)
    app.command(name="status")(scan.status_cmd)
    app.command(name="import")(imp.import_data)
    app.command(name="clean")(clean.clean)
    app.add_typer(_import_stats().app, name="stats")
    app.add_typer(_import_text().app, name="text")
    app.add_typer(_import_ai().app, name="ai")
    app.add_typer(_import_network().app, name="network")
    app.add_typer(_import_config().app, name="config")
    app.add_typer(_import_export().app, name="export")
    app.add_typer(_import_trend().app, name="trend")
    app.add_typer(_import_report().app, name="report")
    app.add_typer(_import_interactive().app, name="interactive")
    app.add_typer(_import_run().app, name="run")
    app.command(name="query")(_import_query_cmd())
    app.add_typer(_import_compare().app, name="compare")
    app.add_typer(_import_serve().app, name="serve")
    app.add_typer(_import_plugins().app, name="plugins")
    app.add_typer(_import_pdf().app, name="pdf")
```

- [ ] **Step 2: 在 `help.py` 的 `_GROUPS` 中加入 `pdf` 组**

在 `_GROUPS` 列表末尾添加：

```python
    ("pdf", "PDF 全文分析", [
        ("extract", "批量提取 PDF 文本"),
    ]),
```

- [ ] **Step 3: 提交**

```bash
git add src/citationer/cli/main.py src/citationer/cli/help.py
git commit -m "feat(cli): register pdf command group and update L1 help"
```

---

### Task 5: 添加提取器单元测试

**Files:**
- Create: `tests/test_pdf_extractor.py`

**Interfaces:**
- Consumes: `citationer.pdf.extractor.PdfExtractor`
- Produces: 测试通过

- [ ] **Step 1: 创建 `tests/test_pdf_extractor.py`**

```python
"""Tests for citationer.pdf.extractor.PdfExtractor."""

from __future__ import annotations

from pathlib import Path

import pytest

from citationer.pdf.extractor import PdfExtractor


class FakePage:
    def __init__(self, text: str) -> None:
        self._text = text

    def extract_text(self) -> str:
        return self._text


class FakeReader:
    def __init__(self, pages: list[FakePage]) -> None:
        self.pages = pages


def _make_fake_reader(texts: list[str]):
    return FakeReader([FakePage(t) for t in texts])


class TestPdfExtractor:
    def test_extract_file_success(self, tmp_path: Path, monkeypatch):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"fake")

        monkeypatch.setattr(
            "citationer.pdf.extractor.PdfReader",
            lambda _p: _make_fake_reader(["Hello world", "Second page"]),
        )

        extractor = PdfExtractor()
        result = extractor.extract_file(pdf_path)

        assert result["status"] == "success"
        assert result["filename"] == "test.pdf"
        assert result["page_count"] == 2
        assert "Hello world" in result["text"]
        assert "Second page" in result["text"]
        assert result["word_count"] == 4

    def test_extract_file_error(self, tmp_path: Path, monkeypatch):
        pdf_path = tmp_path / "broken.pdf"
        pdf_path.write_bytes(b"fake")

        def _raise(_p):
            raise RuntimeError("corrupted file")

        monkeypatch.setattr("citationer.pdf.extractor.PdfReader", _raise)

        extractor = PdfExtractor()
        result = extractor.extract_file(pdf_path)

        assert result["status"] == "error"
        assert "corrupted file" in result["error"]

    def test_extract_directory_recursive(self, tmp_path: Path, monkeypatch):
        (tmp_path / "a").mkdir()
        (tmp_path / "b").mkdir()
        (tmp_path / "a" / "1.pdf").write_bytes(b"fake")
        (tmp_path / "b" / "2.pdf").write_bytes(b"fake")

        def _fake_reader(p: str):
            path = Path(p)
            if path.name == "1.pdf":
                return _make_fake_reader(["page one"])
            return _make_fake_reader(["page two"])

        monkeypatch.setattr("citationer.pdf.extractor.PdfReader", _fake_reader)

        extractor = PdfExtractor(recursive=True)
        result = extractor.extract_directory(tmp_path)

        assert result["summary"]["total"] == 2
        assert result["summary"]["success"] == 2
        assert result["summary"]["failed"] == 0

    def test_extract_directory_non_recursive(self, tmp_path: Path, monkeypatch):
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "nested.pdf").write_bytes(b"fake")
        (tmp_path / "root.pdf").write_bytes(b"fake")

        monkeypatch.setattr(
            "citationer.pdf.extractor.PdfReader",
            lambda _p: _make_fake_reader(["text"]),
        )

        extractor = PdfExtractor(recursive=False)
        result = extractor.extract_directory(tmp_path)

        assert result["summary"]["total"] == 1
        filenames = [f["filename"] for f in result["files"]]
        assert "root.pdf" in filenames
        assert "nested.pdf" not in filenames

    def test_extract_directory_not_a_directory(self, tmp_path: Path):
        extractor = PdfExtractor()
        with pytest.raises(ValueError, match="Not a directory"):
            extractor.extract_file(tmp_path)

    def test_max_chars_truncation(self, tmp_path: Path, monkeypatch):
        pdf_path = tmp_path / "long.pdf"
        pdf_path.write_bytes(b"fake")

        monkeypatch.setattr(
            "citationer.pdf.extractor.PdfReader",
            lambda _p: _make_fake_reader(["abcdefghij"]),
        )

        extractor = PdfExtractor(max_chars=5)
        result = extractor.extract_file(pdf_path)

        assert result["status"] == "success"
        assert result["text"] == "abcde"
```

- [ ] **Step 2: 运行新测试（仅本文件，验证通过）**

```bash
python -m pytest tests/test_pdf_extractor.py -v
```

- [ ] **Step 3: 提交**

```bash
git add tests/test_pdf_extractor.py
git commit -m "test(pdf): add PdfExtractor unit tests"
```

---

### Task 6: 添加 CLI 测试

**Files:**
- Create: `tests/test_pdf_cmd.py`

**Interfaces:**
- Consumes: `typer.testing.CliRunner`, `citationer.cli.main.app`
- Produces: 测试通过

- [ ] **Step 1: 创建 `tests/test_pdf_cmd.py`**

```python
"""Tests for citationer pdf commands."""

from __future__ import annotations

import json
from pathlib import Path

from citationer.cli.main import app


class TestPdfExtractCommand:
    def test_pdf_extract_help(self, cli_runner):
        result = cli_runner.invoke(app, ["pdf", "--help"])
        assert result.exit_code == 0
        assert "extract" in result.output

    def test_pdf_extract_success(self, cli_runner, clean_cwd, monkeypatch, tmp_path):
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "paper.pdf").write_bytes(b"fake")

        def _fake_reader(_p):
            class Page:
                def extract_text(self) -> str:
                    return "Sample PDF content"

            class Reader:
                pages = [Page()]

            return Reader()

        monkeypatch.setattr("citationer.pdf.extractor.PdfReader", _fake_reader)
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(
            app, ["pdf", "extract", str(pdf_dir), "-o", "out.json"]
        )

        assert result.exit_code == 0, result.output
        assert "处理完成" in result.output
        assert Path("out.json").exists()

        data = json.loads(Path("out.json").read_text(encoding="utf-8"))
        assert data["summary"]["success"] == 1
        assert data["files"][0]["filename"] == "paper.pdf"
        assert "Sample PDF content" in data["files"][0]["text"]

    def test_pdf_extract_empty_dir(self, cli_runner, clean_cwd, tmp_path):
        pdf_dir = tmp_path / "empty"
        pdf_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(
            app, ["pdf", "extract", str(pdf_dir), "-o", "empty.json"]
        )

        assert result.exit_code == 0, result.output
        assert Path("empty.json").exists()
        data = json.loads(Path("empty.json").read_text(encoding="utf-8"))
        assert data["summary"]["total"] == 0

    def test_pdf_extract_error_file(self, cli_runner, clean_cwd, monkeypatch, tmp_path):
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "broken.pdf").write_bytes(b"fake")

        def _raise(_p):
            raise RuntimeError("boom")

        monkeypatch.setattr("citationer.pdf.extractor.PdfReader", _raise)
        monkeypatch.chdir(tmp_path)

        result = cli_runner.invoke(
            app, ["pdf", "extract", str(pdf_dir), "-o", "err.json"]
        )

        assert result.exit_code == 0, result.output
        data = json.loads(Path("err.json").read_text(encoding="utf-8"))
        assert data["summary"]["total"] == 1
        assert data["summary"]["failed"] == 1
        assert data["errors"][0]["status"] == "error"
```

- [ ] **Step 2: 运行新测试（仅本文件，验证通过）**

```bash
python -m pytest tests/test_pdf_cmd.py -v
```

- [ ] **Step 3: 提交**

```bash
git add tests/test_pdf_cmd.py
git commit -m "test(cli): add pdf extract command tests"
```

---

### Task 7: 代码风格检查

**Files:**
- 所有已修改文件

**Interfaces:**
- Consumes: 无
- Produces: `ruff check src/ tests/` 通过

- [ ] **Step 1: 运行 ruff 检查**

```bash
ruff check src/ tests/
```

- [ ] **Step 2: 修复所有报错（如有）**

- [ ] **Step 3: 提交修复**

```bash
git add -A
git commit -m "style: fix ruff issues for pdf feature"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ 递归扫描 PDF — Task 2
- ✅ 使用 pypdf 提取文本 — Task 2
- ✅ 输出 JSON 含 filename/path/page_count/word_count/text/status — Task 2
- ✅ 错误隔离 — Task 2
- ✅ CLI 命令 `citationer pdf extract` — Task 3/4
- ✅ `--output`, `--recursive`, `--max-chars` 参数 — Task 3
- ✅ pypdf 依赖放在 `text` 和 `all` 组 — Task 1
- ✅ L1 Help 更新 — Task 4

**2. Placeholder scan:** 无 TBD/TODO/"implement later" 等占位符。

**3. Type consistency:**
- `PdfExtractor.__init__` 签名在 Task 2 与 Task 3 CLI 调用一致
- `extract_directory` 返回结构在 extractor、CLI、测试中一致
- 命令注册使用 `_import_pdf().app` 与 `name="pdf"`

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-27-p5-4-pdf-extraction.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
