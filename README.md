# Citationer

> Citationer — A one-click bibliometric analysis CLI tool.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/citationer.svg)](https://pypi.org/project/citationer/)

**Citationer** 是一个面向科研工作者的轻量级、本地化、零配置文献分析工具。进入包含题录文件的目录，运行一条命令，即可获得从描述统计到知识图谱的完整文献分析报告。

Citationer — A one-click bibliometric analysis CLI tool. Auto-detects CNKI, Web of Science, and Scopus export formats; delivers descriptive statistics, co-occurrence/collaboration networks, AI-powered topic labeling via DeepSeek, and one-shot Markdown/HTML/PDF report generation.

## ✨ 特性

- 🔍 **自动格式检测** — 支持 CNKI、Web of Science、Scopus 等多种题录格式
- 📊 **描述统计分析** — 年度趋势、高产作者/期刊/机构、引用分析
- 🔗 **网络分析** — 关键词共现、作者合作、共被引网络
- 🤖 **AI 增强** — 集成 DeepSeek 大模型进行主题标注和综述生成
- 📝 **报告生成** — 一键生成 Markdown/HTML/PDF 报告
- 🎨 **Rich 终端界面** — 彩色表格、进度条、交互式输出
- 📦 **管道友好** — 输出结果可被 `grep`、`jq` 等标准 Unix 工具处理

## 📦 安装

```bash
# 推荐: 使用 pipx 隔离安装
pipx install citationer

# 或使用 pip
pip install citationer

# 或从源码安装
git clone https://github.com/JasonCENG/citationer.git
cd citationer
pip install -e .
```

## 🚀 快速开始

```bash
# 1. 进入题录文件目录
cd /path/to/your/literature

# 2. 扫描目录中的题录文件
citationer scan

# 3. 导入题录数据
citationer import

# 4. 数据清洗与去重
citationer clean

# 5. 查看统计概览
citationer stats overview

# 6. 年度趋势分析
citationer stats yearly

# 7. 高产期刊 Top-20
citationer stats journals --top 20

# 8. 高产作者 Top-20
citationer stats authors --top 20
```

## 📖 文档

完整文档请访问 [GitHub Wiki](https://github.com/jbiter/citationer/wiki).

## 🛠 开发

```bash
# 安装依赖
poetry install

# 运行测试
poetry run pytest

# 代码检查
poetry run ruff check src/ tests/
poetry run mypy src/citationer/
```

## 📄 许可证

MIT © Jason Yu
