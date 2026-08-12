# Citationer 解析器插件系统设计

> **状态**: 已评审待实现  
> **日期**: 2026-08-12  
> **对应 PRD**: P5-3 插件系统  
> **目标版本**: v5.2.0

## 1. 背景与目标

Citationer 目前内置 9 个解析器，全部硬编码在 `citationer.cli.scan_cmd:get_registry()` 中。P5-3 的目标是让第三方能够贡献解析器，无需修改核心代码即可扩展支持新的题录格式。

本设计选择 **最小可行方案**：只支持解析器插件，保持内置解析器不变，第三方通过标准 `entry_points` 机制注册。

## 2. 设计决策

| 问题 | 决策 | 理由 |
|---|---|---|
| 插件类型 | 仅解析器插件 | 降低复杂度，聚焦真实需求；未来可扩展 |
| 发现机制 | `importlib.metadata.entry_points(group="citationer.parsers")` | Python 标准机制，与 setuptools/poetry 兼容 |
| 内置 vs 插件顺序 | 内置先注册，插件 append | 安全、可预测；不破坏现有行为 |
| 入口点契约 | 指向 callable（类或工厂函数），产物需符合 `BaseParser` 接口 | 简单且灵活 |
| 示例插件 | `examples/endnote-plugin/` 独立包 | 演示真实第三方开发流程 |
| CLI | 新增 `citationer plugins list` | 方便用户查看已加载解析器 |

## 3. 入口点契约

第三方插件的 `pyproject.toml`：

```toml
[project.entry-points."citationer.parsers"]
endnote = "endnote_plugin.parser:EndNoteXMLParser"
```

- 键（`endnote`）是插件 ID，仅用于列表展示，不参与匹配逻辑。
- 值指向的 callable 应满足：
  - 无需参数调用后返回 `BaseParser` 实例；或
  - 本身就是一个 `BaseParser` 子类，框架会自动实例化。

## 4. 核心改动

### 4.1 `ParserRegistry.register_from_entry_points`

```python
def register_from_entry_points(self) -> None:
    """Discover and register third-party parsers via entry points."""
    try:
        from importlib.metadata import entry_points
    except ImportError:  # pragma: no cover
        return

    try:
        eps = entry_points(group="citationer.parsers")
    except TypeError:
        # Python < 3.10 compatibility
        eps = entry_points().get("citationer.parsers", [])

    for ep in eps:
        try:
            factory = ep.load()
            parser = factory() if not isinstance(factory, type) else factory()
            if not isinstance(parser, BaseParser):
                raise TypeError(f"{ep.name} does not produce a BaseParser")
            self.register(parser)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load parser plugin %s: %s", ep.name, exc)
```

### 4.2 `get_registry()` 调用顺序

```python
def get_registry() -> ParserRegistry:
    global _registry
    if _registry is None:
        _registry = ParserRegistry()
        # Built-in parsers first
        _registry.register(CnkiExcelParser())
        ...
        _registry.register(RISParser())
        # Third-party plugins
        _registry.register_from_entry_points()
    return _registry
```

### 4.3 新增 CLI 命令

文件：`src/citationer/cli/plugins_cmd.py`

```bash
citationer plugins list
```

输出示例：

```
已注册的解析器

  来源          解析器
  ───────────────────────────────
  built-in      CNKI
  built-in      Web of Science
  ...
  plugin: endnote-plugin   EndNote
```

- 内置解析器显示 `built-in`。
- 插件显示 `plugin: <distribution_name>`（通过 `ep.dist.name` 获取）。
- 加载失败的插件显示 `error` 及错误信息。

## 5. 示例插件 `examples/endnote-plugin/`

```
examples/endnote-plugin/
├── pyproject.toml
├── README.md
└── endnote_plugin/
    ├── __init__.py
    └── parser.py
```

`pyproject.toml`：

```toml
[project]
name = "endnote-plugin"
version = "0.1.0"
dependencies = ["citationer>=5.2.0"]

[project.entry-points."citationer.parsers"]
endnote = "endnote_plugin.parser:EndNoteXMLParser"
```

`parser.py`：

```python
from pathlib import Path
from citationer.models.record import Record
from citationer.parsers.base import BaseParser


class EndNoteXMLParser(BaseParser):
    @property
    def source_name(self) -> str:
        return "EndNote"

    def detect(self, filepath: Path) -> bool:
        return filepath.suffix.lower() in {".enl", ".xml"}

    def parse(self, filepath: Path) -> list[Record]:
        ...
```

## 6. 测试策略

| 测试 | 方式 |
|---|---|
| 单元测试 | monkeypatch `importlib.metadata.entry_points` 返回 fake entry point |
| 错误路径 | fake entry point 抛出异常，验证 CLI 不崩溃且显示 warning |
| 集成测试 | 将 `examples/endnote-plugin/` 加入 `PYTHONPATH` 或临时安装，验证 `plugins list` 能发现 |
| 内置不受影响 | 验证内置解析器顺序和检测结果不变 |

## 7. 任务清单

- [ ] 扩展 `ParserRegistry`：新增 `register_from_entry_points()`
- [ ] 修改 `get_registry()`：注册内置后扫描 entry points
- [ ] 新增 `src/citationer/cli/plugins_cmd.py` 与 `citationer plugins list`
- [ ] 在 `src/citationer/cli/main.py` 注册 `plugins` 命令组
- [ ] 创建 `examples/endnote-plugin/` 示例包
- [ ] 补充单元/集成测试
- [ ] 更新文档（README / site/docs）
- [ ] 本地验证：ruff + pytest + build
- [ ] 发布 v5.2.0

## 8. 风险与回退

- **风险**：entry point 加载失败导致整个 registry 不可用。  
  **缓解**：单个插件失败只记录 warning，不影响其他解析器。
- **风险**：插件依赖未安装。  
  **缓解**：插件自身声明依赖，citationer 不强制安装；`plugins list` 显示错误信息。
- **回退**：如果 entry points 机制不可用（极旧 Python），`register_from_entry_points()` 直接返回，不影响内置功能。
