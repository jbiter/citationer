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
