# Citationer v5 — 用户手册

> **终端优先的文献题录分析 CLI 工具** —— 从原始导出文件到分析洞察。

---

## 目录

1. [概述](#1-概述)
2. [安装](#2-安装)
3. [快速开始](#3-快速开始)
4. [数据管理](#4-数据管理)
5. [描述性统计分析](#5-描述性统计分析)
6. [文本挖掘与 NLP](#6-文本挖掘与-nlp)
7. [网络分析](#7-网络分析)
8. [LLM 驱动的 AI 分析](#8-llm-驱动的-ai-分析)
9. [配置管理](#9-配置管理)
10. [趋势分析](#10-趋势分析)
11. [报告生成](#11-报告生成)
12. [导出与互操作](#12-导出与互操作)
13. [支持的题录格式](#13-支持的题录格式)
14. [帮助系统](#14-帮助系统)

---

## 1. 概述

**Citationer** 是一个面向科研工作者、学生和图书馆员的终端优先文献计量分析工具。它自动化了整个分析流程：

```
原始导出文件  →  解析与统一  →  清洗与去重  →  分析  →  导出
```

### 架构

```
┌─────────────────────────────────────────┐
│              CLI 层 (Typer + Rich)       │
├─────────────────────────────────────────┤
│  Stats Engine  │  Text Engine  │  Network Engine
├─────────────────────────────────────────┤
│  解析器 (CNKI, WoS)  │  去重引擎          │
├─────────────────────────────────────────┤
│  SQLite 缓存  │  配置 (YAML)  │  LLM 客户端
└─────────────────────────────────────────┘
```

### 核心设计原则

- **开箱即用**: 自动检测文件格式，默认行为覆盖 80% 的分析需求
- **本地优先**: 所有数据本地处理；LLM 功能为可选项，带隐私保护
- **管道友好**: JSON/CSV/GEXF/GraphML 导出，兼容标准 Unix 工具
- **渐进复杂度**: 简单命令处理常见任务，子命令提供深度分析

---

## 2. 安装

### 环境要求

- Python 3.11 或更高版本
- pip 或 pipx

### 快速安装

```bash
pipx install citationer          # 推荐（隔离安装）
pip install citationer           # 标准 pip 安装
```

### 完整安装（全部可选功能）

```bash
pip install "citationer[all]"
```

这会安装以下依赖：
- `jieba` — 中文分词
- `scikit-learn`、`gensim` — 主题建模与聚类
- `networkx`、`python-louvain`、`plotly` — 网络分析与可视化
- `openai` — LLM API 客户端
- `wordcloud` — 词云生成

### 验证安装

```bash
citationer --help
```

---

## 3. 快速开始

核心工作流仅需 4 条命令：

```bash
cd /path/to/your/literature     # 1. 进入题录文件目录
citationer scan                 # 2. 扫描题录文件
citationer import               # 3. 导入数据
citationer stats overview       # 4. 查看概览仪表盘
```

### 预期输出

```
📁 扫描结果: /path/to/literature
┌──────────────────────┬────────┬────────┬──────────────┐
│ 文件名               │ 来源   │ 条目数 │ 年份范围     │
├──────────────────────┼────────┼────────┼──────────────┤
│ wos_core.txt         │ WoS    │ 156    │ 2015 - 2024  │
│ cnki_export.xlsx     │ CNKI   │ 234    │ 2018 - 2025  │
└──────────────────────┴────────┴────────┴──────────────┘

📊 文献全景概览
┏━━━━━━━━━━━━━━┳━━━━━━┓
┃ 指标         ┃ 数值 ┃
┡━━━━━━━━━━━━━━╇━━━━━━┩
│ 总文献数     │  390 │
│ 覆盖年份     │ 2015 ~ 2025 │
│ 作者总数     │ 1234 │
│ h-index      │   42 │
...
```

---

## 4. 数据管理

### `scan` — 扫描题录文件

递归扫描目录中的受支持文件类型，自动识别来源数据库和格式。

```bash
citationer scan                  # 当前目录
citationer scan /path/to/data    # 指定目录
citationer scan --no-recursive   # 仅扫描顶层目录
```

**输出**: 表格显示每个文件的文件名、识别来源、条目数和年份范围。

### `status` — 快速查看

`scan` 的快速非递归版本。

```bash
citationer status
```

### `import` — 导入数据

解析检测到的文件，将统一格式的记录存入本地 SQLite 数据库（`.citationer/cache.db`）。

```bash
citationer import                         # 导入 — 默认清除已有数据
citationer import file1.txt file2.xlsx    # 导入指定文件
citationer import --keep                  # 追加到已有数据
```

### `clean` — 数据清洗与去重

执行数据质量检查和 4 层去重。

```bash
citationer clean                          # 完整清洗：验证 + 去重
citationer clean --no-check-duplicates    # 仅验证
citationer clean --no-check-missing       # 仅去重
citationer clean --dry-run                # 预览模式，不执行合并
```

**去重策略**:

| 层级 | 方法 | 动作 |
|------|------|------|
| 1 | DOI 精确匹配 | 自动合并 |
| 2 | 标题相似度 ≥ 85% + 年份一致 | 自动合并 |
| 3 | 标题相似度 ≥ 70% + 第一作者相同 + 年份一致 | 自动合并（记录日志供审核） |
| 4 | 跨语言：作者姓氏 + 年份 + 期刊 + 卷页 | 自动合并 |

**验证检查**:
- 缺少标题 / 年份 / 作者
- 年份异常（超出 1900–2030 范围）

---

## 5. 描述性统计分析

所有统计命令从本地数据库读取数据。请先运行 `citationer import`。

### `stats overview` — 全景仪表盘

```bash
citationer stats overview
```

**输出**: 总文献数、年份范围、期刊数量、去重作者数、独著/合著率、机构/国家数、语言分布、文献类型分布、平均引用次数、h-index。

### `stats yearly` — 年度发表趋势

```bash
citationer stats yearly                  # 年度发表量
citationer stats yearly --cumulative     # 含累积曲线
```

包含线性趋势斜率（年均发文增量）。

### `stats journals` — 期刊排名

```bash
citationer stats journals --top 20       # 高产期刊 Top-20
```

### `stats authors` — 作者分析

```bash
citationer stats authors --top 20        # 高产作者 Top-20
```

**附加指标**:
- **Price 定律核心作者**: `发文量 ≥ 0.749 × √(最高产作者发文量)`
- **作者 h-index**: 基于数据集内引用数据
- **独著/合著率**: 独著与合著论文占比
- **第一作者分布**: 谁作为第一作者发表最多

### `stats institutions` — 机构排名

```bash
citationer stats institutions --top 20   # 高产机构 Top-20
```

---

## 6. 文本挖掘与 NLP

### `text preprocess` — 文本预处理

自动检测语言（中文/英文），分词，去除停用词。

```bash
citationer text preprocess               # 处理所有字段（标题 + 摘要）
citationer text preprocess --field title # 仅处理标题
citationer text preprocess --lang zh     # 强制中文分词
citationer text preprocess --lang en     # 强制英文分词
citationer text preprocess --top 10      # 显示前 10 条样例
```

**中文**: jieba 分词 + 内建学术停用词表（约 250 词）。
**英文**: 内建正则分词器 + 词形还原；如已安装 spaCy（`en_core_web_sm`）则优先使用。

### `text keywords` — 关键词频次分析

```bash
citationer text keywords --top 50        # Top-50 高频关键词
citationer text keywords --min-count 3   # 过滤低频关键词
citationer text keywords --per-year      # 含关键词×年份热力图
citationer text keywords --format json --output keywords.json
```

### `text topics` — 主题建模

```bash
citationer text topics --method lda      # LDA 主题模型 (gensim)
citationer text topics --method nmf      # NMF 主题模型 (scikit-learn)
citationer text topics --num-topics 8    # 指定主题数量
citationer text topics --max-terms 15    # 每个主题显示的关键词数
```

**自动确定主题数**: 未指定 `--num-topics` 时，引擎根据词汇量自动计算最优主题数（上限 15）。
**一致性分数**: LDA 输出 `c_v` 一致性分数用于质量评估。

### `text summarize` — 提取式摘要

基于 TF-IDF 的关键句提取——无需 LLM，离线可用。

```bash
citationer text summarize --max-sentences 10
citationer text summarize --output summary.txt
```

### `text cluster` — 文献聚类

基于标题+摘要相似度对文献进行聚类。

```bash
citationer text cluster --method kmeans        # K-Means（默认）
citationer text cluster --method hierarchical  # 层次聚类
citationer text cluster --n-clusters 5         # 指定聚类数
citationer text cluster --vectorizer tfidf     # TF-IDF 向量化（默认）
citationer text cluster --output clusters.csv
```

输出轮廓系数、各类大小和代表性词汇。

---

## 7. 网络分析

所有网络命令支持 CSV、GEXF、GraphML 导出，以及通过 Plotly 生成的交互式 HTML 可视化。

### `network keywords` — 关键词共现网络

```bash
citationer network keywords --top 50 --threshold 3
citationer network keywords --output-format gexf --output keywords.gexf
citationer network keywords --viz --output network.html
```

**参数**:
- `--top N`: 仅包含 Top-N 最高频关键词
- `--threshold N`: 边的最少共现次数

### `network coauthors` — 合作网络

```bash
# 作者合作网络
citationer network coauthors --min-papers 2
citationer network coauthors --min-papers 5 --output-format csv

# 机构合作网络
citationer network coauthors --type institutions --min-papers 3
citationer network coauthors --type institutions --viz --output inst_net.html
```

内置 **Louvain 社区检测**——HTML 导出中节点按社区着色。

### `network cocitation` — 共被引分析

两篇文献被同一篇论文引用即构成共被引关系。需要题录包含参考文献数据（WoS 完整记录导出通常包含；CNKI 导出不包含）。

```bash
citationer network cocitation --top 30
```

### `network coupling` — 文献耦合分析

两篇文献共享参考文献即构成耦合关系。参考文献数据不可用时自动降级为关键词耦合。

```bash
citationer network coupling --top 30
citationer network coupling --output-format gexf --viz
```

### 导出格式

| 格式 | 用途 |
|------|------|
| `csv` | 边列表，用于表格分析 |
| `gexf` | 导入 Gephi |
| `graphml` | 导入 Cytoscape |
| `html`（通过 `--viz`） | Plotly 力导向交互图，单文件自包含 |

---

## 8. LLM 驱动的 AI 分析

需要 LLM API Key。配置方法参见[配置管理](#9-配置管理)。

### 隐私设计

仅将**标题和摘要**发送给 LLM。作者姓名、邮箱、所属机构、DOI 和源文件名在传输前**全部剥离**。所有响应按输入哈希本地缓存，避免重复 API 调用。

### `ai topics` — 主题标注

在本地运行 LDA 主题建模，然后将主题关键词发送给 LLM 生成人类可读标签。

```bash
citationer ai topics --auto-label --num-topics 5
citationer ai topics --auto-label --dry-run   # 预览模式，不调用 API
```

**重要提示**: 仅主题关键词被发送给 LLM——不会发送完整的论文记录。每次调用仅消耗约 500-1000 token。

### `ai summarize` — 文献综述生成

基于标题和摘要生成 200-500 字的文献综述。

```bash
citationer ai summarize                     # 默认：前 100 条记录
citationer ai summarize --max-records 50    # 限制输入数量
citationer ai summarize --language zh       # 中文输出
citationer ai summarize --dry-run           # 预览即将发送的内容
```

### `ai trends` — 研究趋势识别

对比早期与近期文献，识别研究焦点的转移、新兴话题和衰退领域。

```bash
citationer ai trends
citationer ai trends --window 5             # 5 年对比窗口
citationer ai trends --dry-run
```

### `ai classify` — 多维度分类

按可配置维度（研究方法、理论框架、应用领域等）对文献进行分类。

```bash
citationer ai classify
citationer ai classify --dimensions "methods,theories,applications"
citationer ai classify --dry-run
```

### `ai info` — LLM 状态查看

```bash
citationer ai info
```

显示：API Key 状态（脱敏）、模型、端点、温度参数、最大 Token 数、缓存统计。

### Token 预算保护

LLM 客户端默认执行 **200,000 字符**的输入上限（约 50K token）。超出此限额时，记录会自动截断并附带说明。使用 `--max-records` 显式控制输入量。`ai topics` 命令仅发送主题关键词（0 条记录），因此永远不会触发限额。

---

## 9. 配置管理

### 配置文件

Citationer 将配置存储在 `.citationer/config.yaml`（在当前目录自动创建）。

### CLI 命令

```bash
citationer config show                          # 查看所有配置
citationer config set llm.api_key sk-xxx        # 设置 API Key
citationer config set llm.model deepseek-chat   # 设置模型
citationer config set llm.base_url https://api.openai.com/v1  # 设置端点
citationer config set llm.temperature 0.5       # 设置温度参数
citationer config set llm.max_tokens 8192       # 设置最大输出 Token 数
citationer config init                          # 创建默认配置文件
citationer config init --force                  # 覆盖已有配置文件
```

### 全部 LLM 可配置项

| 配置键 | 说明 | 默认值 |
|--------|------|--------|
| `llm.api_key` | API Key（必填） | `""` |
| `llm.model` | 模型名称 | `deepseek-chat` |
| `llm.base_url` | API 端点 URL | `https://api.deepseek.com` |
| `llm.temperature` | 生成温度 (0.0–2.0) | `0.3` |
| `llm.max_tokens` | 最大输出 Token 数 | `4096` |

### 环境变量（覆盖配置文件）

| 环境变量 | 覆盖配置项 |
|----------|-----------|
| `CITATIONER_LLM_API_KEY` | `llm.api_key` |
| `CITATIONER_LLM_MODEL` | `llm.model` |
| `CITATIONER_LLM_BASE_URL` | `llm.base_url` |
| `CITATIONER_LLM_TEMPERATURE` | `llm.temperature` |
| `CITATIONER_LLM_MAX_TOKENS` | `llm.max_tokens` |
| `DEEPSEEK_API_KEY` | `llm.api_key`（旧版兼容，优先级更低） |

### 优先级

```
环境变量  >  配置文件 (.citationer/config.yaml)  >  默认值
```

### 提供商配置示例

```bash
# DeepSeek（默认）
citationer config set llm.base_url https://api.deepseek.com
citationer config set llm.model deepseek-chat

# OpenAI
citationer config set llm.base_url https://api.openai.com/v1
citationer config set llm.model gpt-4o

# Ollama（本地部署）
citationer config set llm.base_url http://localhost:11434/v1
citationer config set llm.model llama3
citationer config set llm.api_key ollama    # Ollama 不需要真实 Key
```

---

## 10. 趋势分析

### `trend hotspots` — 关键词突变检测

识别在特定时间段内突然高频出现的关键词，揭示新兴研究热点。

```bash
citationer trend hotspots --top 30        # 分析前 30 个高频关键词
citationer trend hotspots --gamma 0.5     # 更敏感（检测微弱突变）
citationer trend hotspots --min-years 3   # 最少持续 3 年
```

**参数**:
- `--top N`: 分析的关键词数量（默认 30）
- `--gamma`: 灵敏度（0.5 = 敏感，2.0 = 仅强突变）
- `--min-years`: 最少持续年数

**输出**: 突变关键词表格，包含爆发区间、强度和趋势方向（📈 上升 / 📉 下降）。

### `trend strategy` — 战略坐标图

构建关键词共现网络，检测主题聚类，绘制向心度 × 密度四象限图。

```bash
citationer trend strategy --top 50        # 分析前 50 个关键词
```

**四象限**:
| 象限 | 名称 | 含义 |
|------|------|------|
| Q1 (高C, 高D) | 🚀 主流主题 | 发展成熟，处于核心位置 |
| Q2 (低C, 高D) | 🔬 边缘主题 | 发展成熟但较孤立 |
| Q3 (低C, 低D) | 🌱 新兴/衰退 | 发展不足，连接薄弱 |
| Q4 (高C, 低D) | 📚 基础主题 | 重要但发展不足 |

**输出**: 主题表格（含向心度/密度分数）+ 终端散点图。

---

---

## 11. 报告生成

### `report quick` — 快速报告

生成包含所有分析结果的 Markdown 或 HTML 报告。

```bash
citationer report quick -o report.md       # Markdown 报告
citationer report quick -o report.html     # HTML 报告
citationer report quick --enhance -o r.md  # LLM 增强，AI 生成研究发现章节
```

**报告内容**: 概览、年度趋势、高产期刊/作者、关键词、主题建模、共现网络。

### `report custom` — 自定义报告

使用 YAML 配置文件定制报告内容。

```bash
citationer report custom config.yaml -o report.md
```

**示例 config.yaml**:
```yaml
title: "我的文献分析报告"
sections:
  - overview
  - yearly
  - journals
  - authors
  - keywords
  - topics
```

---

## 12. 导出与互操作

### 网络导出格式

| 命令 | 选项 | 输出 |
|------|------|------|
| `network keywords` | `--output-format csv` | 边列表 CSV |
| `network keywords` | `--output-format gexf` | Gephi 兼容 GEXF |
| `network keywords` | `--output-format graphml` | Cytoscape 兼容 GraphML |
| `network keywords` | `--viz` | Plotly 交互式 HTML |
| `network coauthors` | `--viz` | 按社区着色的 HTML 图 |

### 文本分析导出

```bash
citationer text keywords --format json --output keywords.json
citationer text topics --output topics.json
citationer text cluster --output clusters.csv
```

### 管道友好输出

所有表格输出均可与标准 Unix 工具组合使用：

```bash
citationer stats journals --top 30 | grep "Nature"
citationer text keywords --format json | jq '.keywords[:5]'
```

---

## 13. 支持的题录格式

| 来源 | 格式 | 扩展名 | 解析器 | 状态 |
|------|------|--------|--------|------|
| Web of Science | 纯文本（标记格式） | `.txt`、`.ciw` | `WosTextParser` | ✅ |
| Web of Science | 制表符分隔 | `.txt`、`.tsv`、`.csv` | `WosTabDelimitedParser` | ✅ |
| Web of Science | Excel 导出 | `.xlsx`、`.xls` | `WosExcelParser` | ✅ |
| CNKI（知网） | Excel 导出 | `.xlsx` | `CnkiExcelParser` | ✅ |
| Scopus | CSV/Excel | `.csv`、`.xlsx` | `ScopusParser` | ✅ |
| PubMed | XML/MEDLINE | `.xml`、`.nbib` | `PubMedParser` | ✅ |
| CSSCI | Excel/Text | `.xlsx`、`.txt`、`.csv` | `CssciParser` | ✅ |
| BibTeX | 通用格式 | `.bib` | `BibTeXParser` | ✅ |
| RIS | 通用格式 | `.ris`、`.txt` | `RISParser` | ✅ |

### CNKI 文件识别

CNKI Excel 导出通过特征中文列标题（题名、作者、来源、关键词、摘要等）识别。至少需匹配 3 个特征标题。

### WoS 文件识别

- **标记文本**: 首行以 `FN ` 开头，或包含有效 WoS 字段标记（`PT `、`AU ` 等）
- **制表符分隔**: 首行包含制表符分隔的字段标记（`PT\tAU\tTI\t...`）
- **Excel**: 表头包含英文标记如 "Publication Type"、"Authors"、"Article Title"

---

## 14. 帮助系统

Citationer 提供三级帮助体系：

### L1 — 全览 (`citationer --help`)

按功能域分组显示所有一级命令，附快速开始示例和全局选项。

```bash
citationer --help
citationer              # 无参数运行效果相同
```

### L2 — 命令组 (`citationer <group> --help`)

显示命令组内的所有子命令及其描述。

```bash
citationer stats --help
citationer network --help
citationer ai --help
```

### L3 — 命令详情 (`citationer <group> <cmd> --help`)

显示完整参数列表，包括类型、默认值和使用示例。

```bash
citationer stats yearly --help
citationer text topics --help
citationer network keywords --help
```

---

## 附录：数据目录结构

```
your-project/
├── data/                       # 你的题录文件
│   ├── wos_export.txt
│   └── cnki_2024.xlsx
├── .citationer/                # 自动生成（加入 .gitignore）
│   ├── cache.db                # SQLite 数据库
│   ├── cache.db-shm            # SQLite WAL 文件
│   ├── cache.db-wal            # SQLite WAL 文件
│   └── config.yaml             # 你的配置文件
└── citationer_output/          # 默认报告输出目录
```

---

*Citationer v5 — 2026年7月*
