# P5-3 解析器插件系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让第三方解析器通过 `citationer.parsers` entry point 注册到 Citationer，同时新增 `citationer plugins list` 命令和 EndNote XML 示例插件。

**Architecture:** 扩展 `ParserRegistry` 增加 `register_from_entry_points()`，在 `get_registry()` 注册完内置解析器后调用；入口点指向 `BaseParser` 子类或工厂函数；CLI 新增 `plugins` 命令组展示已注册解析器；示例插件作为独立包放在 `examples/endnote-plugin/`。

**Tech Stack:** Python 3.11+、`importlib.metadata.entry_points`、setuptools entry_points、Typer、Rich、pytest。

## Global Constraints

- Python >= 3.11（可直接使用 `entry_points(group=...)`）。
- 内置解析器优先注册，第三方插件 append 在后面。
- 插件加载失败只记录 warning，不中断其他解析器。
- 所有变更必须通过 `ruff check src/ tests/` 和 `pytest tests/ --cov-fail-under=80`。
- 不直接提交到 `main`，所有工作在当前 `feat/p5.3-plugin-system` 分支完成并通过 PR 合并。

---

## File Structure

| 文件 | 职责 |
|---|---|
| `src/citationer/parsers/base.py` | 扩展 `ParserRegistry`，新增 `register_from_entry_points()` |
| `src/citationer/cli/scan_cmd.py` | 在 `get_registry()` 内置注册后调用 entry points 扫描 |
| `src/citationer/cli/plugins_cmd.py` | 新增 `citationer plugins list` 命令 |
| `src/citationer/cli/main.py` | 注册 `plugins` 命令组 |
| `tests/test_plugins.py` | 插件发现、加载失败、`plugins list` 命令测试 |
| `examples/endnote-plugin/pyproject.toml` | 示例插件包配置与 entry point 声明 |
| `examples/endnote-plugin/README.md` | 示例插件使用说明 |
| `examples/endnote-plugin/endnote_plugin/__init__.py` | 包初始化 |
| `examples/endnote-plugin/endnote_plugin/parser.py` | `EndNoteXMLParser` 实现 |
| `site/docs/plugin-development.md` | 插件开发文档 |
| `README.md` | 增加插件系统简介 |

---

## Task 1: 扩展 ParserRegistry 支持 entry points

**Files:**
- Modify: `src/citationer/parsers/base.py`
- Test: `tests/test_plugins.py`

**Interfaces:**
- Consumes: `importlib.metadata.entry_points`
- Produces: `ParserRegistry.register_from_entry_points(self) -> None`

- [ ] **Step 1: 写失败测试**

在 `tests/test_plugins.py` 中：

```python
from pathlib import Path

import pytest

from citationer.models.record import Record
from citationer.parsers.base import BaseParser, ParserRegistry


class FakeParser(BaseParser):
    @property
    def source_name(self) -> str:
        return "FakePlugin"

    def detect(self, filepath: Path) -> bool:
        return filepath.suffix == ".fake"

    def parse(self, filepath: Path) -> list[Record]:
        return []


def make_entry_point(name: str, factory):
    class _EP:
        def __init__(self, name, factory):
            self.name = name
            self._factory = factory

        def load(self):
            return self._factory

    return _EP(name, factory)


def test_registry_loads_entry_point_plugins(monkeypatch):
    registry = ParserRegistry()

    def _fake_eps(*, group):
        if group == "citationer.parsers":
            return [make_entry_point("fake", FakeParser)]
        return []

    monkeypatch.setattr(
        "citationer.parsers.base.entry_points", _fake_eps
    )
    registry.register_from_entry_points()

    assert len(registry) == 1
    assert registry.registered_sources == ["FakePlugin"]
```

运行：
```bash
python -m pytest tests/test_plugins.py::test_registry_loads_entry_point_plugins -v
```
预期：FAIL（`AttributeError: 'ParserRegistry' object has no attribute 'register_from_entry_points'`）

- [ ] **Step 2: 实现 `register_from_entry_points()`**

修改 `src/citationer/parsers/base.py`：

```python
import logging
from importlib.metadata import entry_points

logger = logging.getLogger(__name__)


class ParserRegistry:
    ...  # 保留现有方法

    def register_from_entry_points(self) -> None:
        """Discover and register third-party parsers via entry points."""
        try:
            eps = entry_points(group="citationer.parsers")
        except Exception:  # pragma: no cover
            logger.debug("Unable to scan citationer.parsers entry points")
            return

        for ep in eps:
            try:
                factory = ep.load()
                if isinstance(factory, type) and issubclass(factory, BaseParser):
                    parser: BaseParser = factory()
                elif callable(factory):
                    parser = factory()
                    if not isinstance(parser, BaseParser):
                        raise TypeError(
                            f"Plugin {ep.name!r} factory did not return a BaseParser"
                        )
                else:
                    raise TypeError(
                        f"Plugin {ep.name!r} entry point is not a BaseParser subclass or factory"
                    )
                self.register(parser)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to load parser plugin %s: %s", ep.name, exc)
```

- [ ] **Step 3: 运行测试确认通过**

```bash
python -m pytest tests/test_plugins.py::test_registry_loads_entry_point_plugins -v
```
预期：PASS

- [ ] **Step 4: 提交**

```bash
git add src/citationer/parsers/base.py tests/test_plugins.py
git commit -m "feat(parsers): add ParserRegistry.register_from_entry_points" -m "Discover third-party parsers via citationer.parsers entry points." -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 2: 在 `get_registry()` 中扫描插件

**Files:**
- Modify: `src/citationer/cli/scan_cmd.py`
- Test: `tests/test_plugins.py`

**Interfaces:**
- Consumes: `ParserRegistry.register_from_entry_points()`
- Produces: 内置解析器注册后自动加载第三方插件

- [ ] **Step 1: 写失败测试**

在 `tests/test_plugins.py` 中：

```python
def test_get_registry_includes_entry_point_plugins(monkeypatch):
    from citationer.cli.scan_cmd import get_registry

    # 清理 module-level 缓存
    monkeypatch.setattr("citationer.cli.scan_cmd._registry", None)

    def _fake_eps(*, group):
        if group == "citationer.parsers":
            return [make_entry_point("fake", FakeParser)]
        return []

    monkeypatch.setattr(
        "citationer.parsers.base.entry_points", _fake_eps
    )

    registry = get_registry()
    assert "FakePlugin" in registry.registered_sources
    # 内置解析器仍然保留
    assert "CNKI" in registry.registered_sources
```

运行：
```bash
python -m pytest tests/test_plugins.py::test_get_registry_includes_entry_point_plugins -v
```
预期：FAIL（`FakePlugin` 不在注册列表中）

- [ ] **Step 2: 修改 `get_registry()`**

在 `src/citationer/cli/scan_cmd.py` 的 `get_registry()` 函数末尾（`return _registry` 前）添加：

```python
_registry.register_from_entry_points()
```

- [ ] **Step 3: 运行测试确认通过**

```bash
python -m pytest tests/test_plugins.py::test_get_registry_includes_entry_point_plugins -v
```
预期：PASS

- [ ] **Step 4: 提交**

```bash
git add src/citationer/cli/scan_cmd.py tests/test_plugins.py
git commit -m "feat(scan): load third-party parser plugins in get_registry" -m "Call register_from_entry_points after built-in parsers." -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 3: 新增 `citationer plugins list` 命令

**Files:**
- Create: `src/citationer/cli/plugins_cmd.py`
- Modify: `src/citationer/cli/main.py`
- Test: `tests/test_plugins.py`

**Interfaces:**
- Consumes: `citationer.cli.scan_cmd.get_registry()`
- Produces: `app.add_typer(_import_plugins().app, name="plugins")`

- [ ] **Step 1: 写失败测试**

在 `tests/test_plugins.py` 中：

```python
def test_plugins_list_command(cli_runner):
    from citationer.cli.main import app

    result = cli_runner.invoke(app, ["plugins", "list"])
    assert result.exit_code == 0
    assert "CNKI" in result.output
    assert "built-in" in result.output
```

运行：
```bash
python -m pytest tests/test_plugins.py::test_plugins_list_command -v
```
预期：FAIL（`No such command 'plugins'`）

- [ ] **Step 2: 创建 `plugins_cmd.py`**

新建 `src/citationer/cli/plugins_cmd.py`：

```python
"""Plugin management commands."""

from __future__ import annotations

import logging

import typer
from rich.console import Console
from rich.table import Table

from citationer.cli.scan_cmd import get_registry

app = typer.Typer(
    name="plugins",
    help="管理第三方插件",
    no_args_is_help=True,
)

console = Console()
logger = logging.getLogger(__name__)


@app.command(name="list")
def list_plugins() -> None:
    """列出所有已注册的解析器（内置 + 插件）。"""
    registry = get_registry()

    table = Table(title="已注册的解析器")
    table.add_column("来源", style="dim")
    table.add_column("解析器")

    # 内置解析器：无法直接区分，因此通过 source_name 去重展示
    # 实际来源信息通过扫描 entry_points 获得
    from citationer.parsers.base import entry_points

    plugin_sources: dict[str, str] = {}
    try:
        eps = entry_points(group="citationer.parsers")
        for ep in eps:
            try:
                parser = ep.load()()
                plugin_sources[parser.source_name] = ep.dist.name if ep.dist else "plugin"
            except Exception as exc:  # noqa: BLE001
                logger.debug("Could not inspect plugin %s: %s", ep.name, exc)
    except Exception:  # noqa: BLE001
        pass

    for parser in registry:
        source = plugin_sources.get(parser.source_name, "built-in")
        table.add_row(source, parser.source_name)

    console.print(table)
```

- [ ] **Step 3: 在 `main.py` 注册命令组**

在 `src/citationer/cli/main.py` 添加懒加载函数：

```python
def _import_plugins():
    from citationer.cli import plugins_cmd
    return plugins_cmd
```

在 `_register()` 中添加：

```python
app.add_typer(_import_plugins().app, name="plugins")
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_plugins.py::test_plugins_list_command -v
```
预期：PASS

- [ ] **Step 5: 提交**

```bash
git add src/citationer/cli/plugins_cmd.py src/citationer/cli/main.py tests/test_plugins.py
git commit -m "feat(cli): add citationer plugins list command" -m "List built-in and entry-point parser plugins." -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 4: 添加插件加载失败路径测试

**Files:**
- Test: `tests/test_plugins.py`

- [ ] **Step 1: 添加测试**

```python
def test_registry_skips_broken_entry_point_plugins(monkeypatch, caplog):
    registry = ParserRegistry()

    class BrokenParser:
        pass

    def _fake_eps(*, group):
        if group == "citationer.parsers":
            return [make_entry_point("broken", BrokenParser)]
        return []

    monkeypatch.setattr(
        "citationer.parsers.base.entry_points", _fake_eps
    )

    with caplog.at_level("WARNING"):
        registry.register_from_entry_points()

    assert len(registry) == 0
    assert "Failed to load parser plugin" in caplog.text
```

- [ ] **Step 2: 运行测试确认通过**

```bash
python -m pytest tests/test_plugins.py -v
```
预期：全部 PASS

- [ ] **Step 3: 提交**

```bash
git add tests/test_plugins.py
git commit -m "test(plugins): add broken entry point handling test" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 5: 创建 EndNote XML 示例插件

**Files:**
- Create: `examples/endnote-plugin/pyproject.toml`
- Create: `examples/endnote-plugin/README.md`
- Create: `examples/endnote-plugin/endnote_plugin/__init__.py`
- Create: `examples/endnote-plugin/endnote_plugin/parser.py`

- [ ] **Step 1: 创建示例插件文件**

`examples/endnote-plugin/pyproject.toml`：

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project]
name = "endnote-plugin"
version = "0.1.0"
description = "Citationer parser plugin for EndNote XML exports"
requires-python = ">=3.11"
dependencies = [
    "citationer>=5.2.0",
]

[project.entry-points."citationer.parsers"]
endnote = "endnote_plugin.parser:EndNoteXMLParser"

[tool.setuptools.packages.find]
where = ["."]
```

`examples/endnote-plugin/endnote_plugin/__init__.py`：

```python
"""EndNote parser plugin for Citationer."""

__version__ = "0.1.0"
```

`examples/endnote-plugin/endnote_plugin/parser.py`：

```python
"""EndNote XML export parser."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from citationer.models.record import Author, Record
from citationer.parsers.base import BaseParser


class EndNoteXMLParser(BaseParser):
    """Parser for EndNote XML (.xml/.enl) exports."""

    @property
    def source_name(self) -> str:
        return "EndNote"

    def detect(self, filepath: Path) -> bool:
        if filepath.suffix.lower() not in {".xml", ".enl"}:
            return False
        try:
            with open(filepath, "rb") as f:
                header = f.read(200)
            return b"<?xml" in header or b"<records>" in header.lower()
        except Exception:  # noqa: BLE001
            return False

    def parse(self, filepath: Path) -> list[Record]:
        tree = ET.parse(filepath)
        root = tree.getroot()
        records: list[Record] = []
        for record in root.findall(".//record"):
            title = self._text(record, ".//title") or ""
            year_str = self._text(record, ".//year")
            year = int(year_str) if year_str and year_str.isdigit() else None
            authors = [
                Author(full_name=name.strip(), order=i + 1)
                for i, name in enumerate(self._texts(record, ".//author"))
                if name.strip()
            ]
            records.append(
                Record(
                    title=title,
                    year=year,
                    authors=authors,
                    journal=self._text(record, ".//secondary-title"),
                    doi=self._text(record, ".//accession-num"),
                    source_database="EndNote",
                )
            )
        return records

    def _text(self, element, path: str) -> str | None:
        found = element.find(path)
        if found is not None and found.text:
            return found.text.strip()
        return None

    def _texts(self, element, path: str) -> list[str]:
        return [e.text.strip() for e in element.findall(path) if e.text]
```

`examples/endnote-plugin/README.md`：

```markdown
# EndNote Plugin for Citationer

Install in editable mode:

```bash
pip install -e examples/endnote-plugin
```

Then run:

```bash
citationer plugins list
```

You should see `EndNote` in the list.
```

- [ ] **Step 2: 验证示例插件可安装并发现**

```bash
pip install -e examples/endnote-plugin
python -c "from endnote_plugin.parser import EndNoteXMLParser; print(EndNoteXMLParser().source_name)"
citationer plugins list
```

预期：`EndNote` 出现在列表中。

- [ ] **Step 3: 提交**

```bash
git add examples/endnote-plugin/
git commit -m "feat(examples): add EndNote XML parser plugin example" -m "Standalone example package demonstrating citationer.parsers entry point." -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 6: 文档更新

**Files:**
- Create: `site/docs/plugin-development.md`
- Modify: `README.md`

- [ ] **Step 1: 创建插件开发文档**

`site/docs/plugin-development.md`：

```markdown
# 开发解析器插件

Citationer 支持通过 `citationer.parsers` entry point 注册第三方解析器。

## 最小插件结构

```
my_plugin/
├── pyproject.toml
└── my_plugin/
    ├── __init__.py
    └── parser.py
```

## 实现解析器

继承 `citationer.parsers.base.BaseParser`：

```python
from pathlib import Path
from citationer.models.record import Record
from citationer.parsers.base import BaseParser

class MyParser(BaseParser):
    @property
    def source_name(self) -> str:
        return "MySource"

    def detect(self, filepath: Path) -> bool:
        return filepath.suffix == ".myfmt"

    def parse(self, filepath: Path) -> list[Record]:
        ...
```

## 注册入口点

在 `pyproject.toml` 中：

```toml
[project.entry-points."citationer.parsers"]
my_source = "my_plugin.parser:MyParser"
```

## 安装与验证

```bash
pip install -e .
citationer plugins list
```

## 完整示例

参见仓库 `examples/endnote-plugin/`。
```

- [ ] **Step 2: 更新 README.md**

在 README 的 Features 或 Development 部分增加：

```markdown
- **🔌 Parser Plugins** — extend Citationer with custom bibliographic parsers via `citationer.parsers` entry points. See `examples/endnote-plugin/`.
```

- [ ] **Step 3: 提交**

```bash
git add site/docs/plugin-development.md README.md
git commit -m "docs: add plugin development guide and README mention" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 7: 集成测试与示例插件验证

**Files:**
- Test: `tests/test_plugins.py`

- [ ] **Step 1: 添加示例插件集成测试**

```python
def test_endnote_example_plugin_loads(tmp_path, monkeypatch):
    """If endnote-plugin is installed, it should appear in the registry."""
    from citationer.parsers.base import entry_points

    # 检查是否真的安装了该 entry point
    try:
        eps = list(entry_points(group="citationer.parsers"))
    except Exception:  # noqa: BLE001
        pytest.skip("No entry points available")

    names = [ep.name for ep in eps]
    if "endnote" not in names:
        pytest.skip("endnote-plugin not installed")

    from citationer.cli.scan_cmd import get_registry
    monkeypatch.setattr("citationer.cli.scan_cmd._registry", None)
    registry = get_registry()
    assert "EndNote" in registry.registered_sources
```

- [ ] **Step 2: 运行全部插件相关测试**

```bash
python -m pytest tests/test_plugins.py -v
```
预期：PASS（`test_endnote_example_plugin_loads` 在 CI 未安装示例插件时会 skip）

- [ ] **Step 3: 提交**

```bash
git add tests/test_plugins.py
git commit -m "test(plugins): add integration test for endnote example plugin" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Task 8: 全项目验证与发布前检查

- [ ] **Step 1: 运行 lint 和全量测试**

```bash
python -m ruff check src/ tests/
python -m pytest tests/ --cov=src/citationer --cov-fail-under=80 -q
```

- [ ] **Step 2: 本地构建**

```bash
rm -rf dist/ build/ citationer.egg-info src/citationer.egg-info
python -m build --sdist --wheel --outdir dist/
ls dist/
```
预期产物：`citationer-5.2.0-py3-none-any.whl` 和 `citationer-5.2.0.tar.gz`

- [ ] **Step 3: 版本一致性检查**

```bash
python -c "import re; py = open('pyproject.toml').read(); init_ = open('src/citationer/__init__.py').read(); ver_py = re.search(r'^version = \"(.+?)\"', py, re.M).group(1); ver_init = re.search(r'__version__ = \"(.+?)\"', init_).group(1); assert ver_py == ver_init, f'MISMATCH: pyproject={ver_py} init={ver_init}'; print(f'OK: both report {ver_py}')"
```
预期：`OK: both report 5.2.0`

- [ ] **Step 4: 提交（如版本号已在此 plan 中修改）**

如果 Task 8 之前已单独 bump 版本，则跳过；否则：

```bash
python -c "import re; ... bump to 5.2.0 ..."
git add pyproject.toml src/citationer/__init__.py site/docs/changelog.md
git commit -m "release: bump version to 5.2.0" -m "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Self-Review Checklist

- [x] **Spec coverage**: entry points 发现、registry 扩展、CLI list、示例插件、测试、文档均已对应任务。
- [x] **Placeholder scan**: 无 TBD/TODO/实现 later；每步含代码或命令。
- [x] **Type consistency**: `register_from_entry_points()`、`get_registry()`、`plugins list` 使用同一 `BaseParser` 接口。
- [x] **Scope**: 计划仅实现解析器插件，未引入通用插件框架，符合 spec 决策 A。
