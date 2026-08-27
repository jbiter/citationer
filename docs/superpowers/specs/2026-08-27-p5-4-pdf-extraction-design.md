# P5-4 PDF 全文分析 — 第一版设计：PDF 文本提取

> **日期**: 2026-08-27  
> **范围**: P5-4 第一阶段，仅实现 PDF 文本提取 CLI 命令  
> **目标版本**: v5.3.0  

---

## 1. 背景与目标

P5-4 计划引入 PDF 全文分析能力。为保持实现简单，第一版仅聚焦「PDF → 纯文本」的最小闭环，为后续全文主题建模、引文上下文分析奠定基础。

**目标**: 用户指定一个目录，工具递归提取所有 PDF 的文本，输出为 JSON，错误文件单独记录但不中断流程。

---

## 2. 功能范围

### 本期实现
- 递归扫描目录中的 `.pdf` 文件
- 使用 `pypdf` 提取每页文本并合并
- 输出 JSON：文件名、路径、页数、字数、文本内容、处理状态
- CLI 命令：`citationer pdf extract <dir> -o output.json`
- 错误隔离：损坏/加密 PDF 进入 `errors` 数组

### 本期不做
- PDF 与题录库匹配关联
- 全文主题建模
- 引文上下文分析
- OCR、图片、表格提取
- 复杂的版式保留

---

## 3. 依赖

新增到 `pyproject.toml`：

```toml
[project.optional-dependencies]
text = [
    "jieba>=0.42",
    "gensim>=4.3",
    "scikit-learn>=1.4",
    "pypdf>=4.0",
]
all = [
    # ... existing
    "pypdf>=4.0",
]
```

选择 `pypdf` 原因：
- BSD-3-Clause 许可证，与 MIT 项目兼容
- 纯 Python，依赖轻
- API 简单，满足第一版纯文本提取需求

---

## 4. CLI 设计

### 命令
```bash
citationer pdf extract ./pdfs/
citationer pdf extract ./pdfs/ -o texts.json
citationer pdf extract ./pdfs/ --recursive=false
citationer pdf extract ./pdfs/ --max-chars 50000
```

### 参数
| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `directory` | `Path` | 必填 | PDF 目录 |
| `--output`, `-o` | `Path` | `pdf_texts.json` | 输出 JSON 文件 |
| `--recursive` | `bool` | `true` | 是否递归子目录 |
| `--max-chars` | `int` | `0`（不截断） | 单个文件最大字符数 |

---

## 5. 输出格式

```json
{
  "files": [
    {
      "filename": "paper1.pdf",
      "path": "./pdfs/paper1.pdf",
      "page_count": 8,
      "word_count": 4200,
      "text": "full extracted text...",
      "status": "success"
    }
  ],
  "errors": [
    {
      "filename": "broken.pdf",
      "path": "./pdfs/broken.pdf",
      "error": "Password protected",
      "status": "error"
    }
  ],
  "summary": {
    "total": 3,
    "success": 2,
    "failed": 1
  }
}
```

---

## 6. 模块设计

### `src/citationer/pdf/extractor.py`
核心类 `PdfExtractor`：

```python
class PdfExtractor:
    def __init__(self, recursive: bool = True, max_chars: int = 0) -> None: ...

    def extract_directory(self, directory: Path) -> dict[str, Any]: ...

    def extract_file(self, filepath: Path) -> dict[str, Any]: ...
```

职责：
- 扫描目录（递归/非递归）
- 逐个提取 PDF 文本
- 捕获异常并生成错误记录
- 返回统一结构

### `src/citationer/cli/pdf_cmd.py`
Typer 命令组：

```python
app = typer.Typer(help="PDF 全文分析")

@app.command("extract")
def extract_command(...) -> None: ...
```

### `src/citationer/cli/main.py`
注册 `pdf` 命令组：

```python
app.add_typer(pdf_cmd.app, name="pdf")
```

---

## 7. 错误处理

| 场景 | 行为 |
|------|------|
| 目录不存在 | 抛出 `typer.BadParameter` |
| 目录下无 PDF | 输出 warning，返回空结果 |
| 文件损坏/加密 | 记录到 `errors`，继续处理其他文件 |
| 提取成功但文本为空 | `status: "success"`，`text: ""` |

---

## 8. 测试策略

- `tests/test_pdf_extractor.py`：测试正常提取、空目录、损坏文件、递归扫描
- `tests/test_pdf_cmd.py`：测试 CLI 参数解析、输出文件生成
- 使用内存中构造的最小 PDF 或 fixture PDF 文件
- 本期暂不测试主题建模（未实现）

---

## 9. 后续迭代方向

- `citationer pdf topics`：基于提取文本做 LDA/NMF 主题建模
- PDF 与题录库匹配（按 DOI / 标题 / 文件名）
- 引文上下文分析

---

## 10. 验收标准

- [ ] `citationer pdf extract ./pdfs/` 可成功提取文本并输出 JSON
- [ ] 递归扫描生效
- [ ] 加密/损坏 PDF 不中断流程
- [ ] `--max-chars` 截断生效
- [ ] ruff lint 通过
- [ ] pytest 通过（覆盖率不强制新增门槛，但新增代码尽量覆盖）
