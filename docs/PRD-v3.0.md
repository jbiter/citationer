# Citationer — 文献题录分析工具 · 产品需求文档 v3.0

> **状态**: Phase 5 进行中（高级功能与生态）
> **作者**: Jason
> **日期**: 2026-07-25
> **合并**: PRD v1.0（原始需求）、PRD v2.0（Phase 2–5 完整规划）、PRD v2.1（终端图表）
> **当前版本**: v5.0.0
> **许可证**: MIT · 开源项目
> **仓库**: github.com/JasonCENG/citationer

---

## 目录

1. [产品愿景与定位](#1-产品愿景与定位)
2. [目标用户](#2-目标用户)
3. [核心概念](#3-核心概念)
4. [功能需求（含实现状态）](#4-功能需求含实现状态)
   - [4.1 数据摄入与解析](#41-数据摄入与解析)
   - [4.2 描述性统计分析](#42-描述性统计分析)
   - [4.3 知识图谱与网络分析](#43-知识图谱与网络分析)
   - [4.4 语义分析与文本挖掘](#44-语义分析与文本挖掘)
   - [4.5 研究脉络与趋势分析](#45-研究脉络与趋势分析)
   - [4.6 可视化输出](#46-可视化输出)
   - [4.7 报告生成](#47-报告生成)
   - [4.8 CLI 交互设计](#48-cli-交互设计)
5. [技术架构（实际）](#5-技术架构实际)
6. [发布与分发策略](#6-发布与分发策略)
7. [开发路线图](#7-开发路线图)
8. [当前质量指标与差距](#8-当前质量指标与差距)
9. [开放问题与决策记录](#9-开放问题与决策记录)

---

## 1. 产品愿景与定位

### 一句话描述

> **`citationer`** —— 一键式文献题录分析 CLI 工具。进入包含题录文件的目录，运行一条命令，即可获得从描述统计到主题挖掘的完整文献分析报告。

### 定位

一个面向科研工作者（研究生、教师、科研人员）的**轻量级、本地化、零配置**文献分析工具。它不替代 CiteSpace、VOSviewer 等专业 GUI 工具，而是提供一种「终端优先」的快速分析体验——适合在日常工作流中快速了解一个文献集合的全貌，或在论文写作初期快速生成统计图表和趋势分析。

### 核心设计原则

| 原则 | 说明 | 当前符合度 |
|------|------|-----------|
| **开箱即用** | 自动检测目录下的题录文件，无需手动指定格式，智能推断 | ✅ 9 个解析器自动识别 |
| **零配置分析** | 默认行为覆盖 80% 的常见分析需求 | ✅ 全命令默认可用 |
| **本地优先** | 所有题录数据在本地处理；LLM 仅上传脱敏摘要 | ✅ SQLite + 本地 NLP |
| **管道友好** | 输出可被 `grep`、`jq` 等 Unix 工具处理 | ✅ JSON/CSV 输出 |
| **渐进复杂度** | 简单事情简单做，复杂分析通过子命令暴露 | ✅ 10 个命令组 |
| **AI 增强** | DeepSeek/OpenAI/Ollama 多提供商 LLM 支持 | ✅ 含缓存与脱敏 |

---

## 2. 目标用户

| 用户画像 | 典型场景 | 核心需求 |
|----------|----------|----------|
| **研究生** | 开题/综述阶段，导师给了一个文献文件夹 | 快速了解领域概况：发表趋势、主要期刊、高产作者与机构 |
| **科研人员** | 写论文时需要做文献计量分析 | 生成符合期刊要求的数据统计图表 |
| **图书馆学科馆员** | 为院系提供学科发展报告 | 批量处理多个数据集，生成标准化报告 |
| **实验室 PI** | 定期追踪研究方向动态 | 趋势检测、新兴话题发现、合作网络分析 |
| **期刊编辑** | 分析期刊发文趋势和作者群 | 机构分布、地区分布、引用分析 |

---

## 3. 核心概念

### 3.1 数据模型

```
题录文件 (Source File)
  └── 题录条目 (Record)
        ├── 元数据字段: title, authors, year, journal, doi, ...
        ├── 内容字段: abstract, keywords, title (用于文本挖掘)
        └── 来源标记: source_type (CNKI/WoS/...), source_file
```

### 3.2 工作流

```
citationer/
├── data/                    # 题录原始文件目录（用户维护）
│   ├── cnki_2024.xlsx
│   ├── wos_search1.txt
│   └── wos_search2.ciw
├── .citationer/             # 工具产生的缓存和配置（自动生成）
│   ├── cache.db             # SQLite 统一数据库（WAL 模式）
│   └── config.yaml          # 用户自定义配置
├── output/                  # 默认输出目录
│   ├── cls/                 # 清洗结果导出
│   └── viz/                 # 图表导出
└── citationer_output/       # 备用报告输出目录
```

### 3.3 支持的题录格式

| 来源 | 格式 | 扩展名 | 状态 |
|------|------|--------|------|
| **CNKI（知网）** | Excel 导出 | `.xlsx`, `.xls` | ✅ 已实现 |
| **Web of Science** | 纯文本 / 制表符分隔 / Excel | `.txt`, `.ciw`, `.xlsx`, `.xls` | ✅ 已实现（3 个解析器） |
| **Scopus** | CSV / Excel | `.csv`, `.xlsx` | ✅ 已实现 |
| **PubMed** | XML / MEDLINE | `.xml`, `.nbib`, `.txt` | ✅ 已实现（XML + MEDLINE 双路径） |
| **CSSCI** | Excel / 文本 | `.xlsx`, `.txt`, `.csv` | ✅ 已实现 |
| **BibTeX** | 通用 | `.bib` | ✅ 已实现 |
| **RIS** | 通用 | `.ris`, `.txt` | ✅ 已实现 |
| **EndNote** | EndNote XML | `.xml` | 🔜 Phase 5 |
| **Zotero** | RDF/CSV | `.rdf`, `.csv` | 🔜 Phase 5 |

---

## 4. 功能需求（含实现状态）

> 标记规范：✅ 已实现　🟡 引擎已有、CLI 未接线　🔜 计划中　❌ 未开始

### 4.1 数据摄入与解析

#### F-1.1 自动扫描与格式检测 ✅

```
$ citationer scan           # 递归扫描当前目录
$ citationer status         # 非递归快速状态
```

- 9 个内置解析器自动注册，按优先级轮询 `detect()`
- Rich 表格输出：文件名、来源、条目数、年份范围
- 无法识别的文件给出提示
- 支持 10 种扩展名：`.xlsx`, `.xls`, `.txt`, `.ciw`, `.csv`, `.bib`, `.ris`, `.xml`, `.nbib`, `.rdf`

#### F-1.2 数据导入与合并 ✅

```
$ citationer import                    # 导入所有检测到的文件
$ citationer import file1.xlsx file2.txt  # 导入指定文件
$ citationer import --keep             # 追加模式（默认清空旧数据）
```

- 统一 Pydantic 数据模型（`Record`，22 个字段）
- 编码自动检测（UTF-8/GBK/GB2312）
- 中文作者姓名归一化
- 批量提交（500 条/批），带 Rich 进度条

**去重策略（4 层）**：

| 层 | 策略 | 阈值 | 行为 |
|----|------|------|------|
| L1 | DOI 精确匹配 | 完全一致 | 自动合并 |
| L2 | 标题模糊 + 同年份 | ≥ 85%（rapidfuzz） | 自动合并 |
| L3 | 标题模糊 + 第一作者 + 同年份 | ≥ 70% | 自动合并（日志记录供审核） |
| L4 | 跨语言（中英文标题）匹配 | 作者+期刊+卷期页码三选二投票 | 自动合并 |

#### F-1.3 数据导出 ✅

```
$ citationer export csv -o data.csv
$ citationer export json -o data.json
$ citationer export bibtex -o refs.bib
$ citationer export ris -o refs.ris
$ citationer export xlsx -o data.xlsx
```

- 5 种导出格式：CSV、JSON、BibTeX、RIS、Excel
- 完整字段映射（含作者、关键词、摘要、引用次数）

#### F-1.4 数据校验与清洗 ✅

```
$ citationer clean                              # 去重 + 缺失检测
$ citationer clean --dry-run                    # 仅检测不合并
$ citationer clean --save                       # 导出清洗后数据为 CSV
$ citationer clean --cache                      # 清空数据库缓存
```

- 缺失关键字段检测（标题/年份/作者），含百分比
- 年份异常检测（1900–2030 范围外）
- 4 层去重（富进度条，分层报告）
- `--save` 导出 `output/cls/cleaned_records.csv`

---

### 4.2 描述性统计分析

#### F-2.1 概览仪表盘 ✅

```
$ citationer stats overview
```

单次遍历输出：总记录数、年份范围、期刊数、作者数（独著/合著率）、机构数、国家数、语言分布、文献类型分布、平均引用次数、h-index。

#### F-2.2 年度趋势 ✅

```
$ citationer stats yearly                    # Braille 折线图
$ citationer stats yearly --cumulative       # 双轴：柱状 + 累积折线
$ citationer stats yearly --table            # 附带数据表格
$ citationer stats yearly --save chart.png   # 导出 PNG
```

#### F-2.3 期刊分析 ✅

```
$ citationer stats journals --top 20
$ citationer stats journals --save chart.png
```

- Top-N 期刊（水平条形图 + 可选表格）
- 期刊总数统计

#### F-2.4 作者分析 ✅

```
$ citationer stats authors --top 20
```

- Top-N 高产作者 + h-index
- Price 定律核心作者识别（`count ≥ 0.749 × √max`）
- 独著/合著统计、平均合作者数
- 第一作者分布

#### F-2.5 机构分析 ✅

```
$ citationer stats institutions --top 20
```

- Top-N 高产机构（条形图 + 可选表格）

#### F-2.6 基金资助分析 🔜

> PRD 原计划功能，尚未实现。依赖 CNKI/WoS/Scopus 的基金字段（已解析入库），需新增 `stats funding` 子命令。

#### F-2.7 引用分析 ✅（基础版）

```
$ citationer stats citations
```

- Top-N 高被引论文
- 引用分布统计（均值、中位数、范围、总量）
- 注：自引率估算未实现

---

### 4.3 知识图谱与网络分析

#### F-3.1 关键词共现网络 ✅

```
$ citationer network keywords --top 50 --threshold 3
$ citationer network keywords --output-format gexf --output graph.gexf
$ citationer network keywords --viz --output network.html
```

- 共现矩阵构建、最小共现阈值过滤
- 导出格式：Table、CSV、GEXF、GraphML、HTML（Plotly 交互图）
- 中英文关键词同时参与

#### F-3.2 合作网络 ✅

```
$ citationer network coauthors --min-papers 2            # 作者合作
$ citationer network coauthors --type institutions        # 机构合作
```

- Louvain 社区检测（种子固定 42）
- HTML 交互图含社区着色
- 多格式导出

#### F-3.3 共被引与文献耦合 ✅

```
$ citationer network cocitation --top 30
$ citationer network coupling --top 30
```

- 共被引：需要参考文献数据（WoS 支持，CNKI 不支持）
- 文献耦合：倒排索引实现 `O(总被引数)` 性能；无参考文献时自动回退到关键词耦合

---

### 4.4 语义分析与文本挖掘

#### F-4.1 关键词分析 ✅

```
$ citationer text keywords --top 30
$ citationer text keywords --per-year               # 年度热力图
$ citationer text keywords --wordcloud -o wc.png   # 词云导出
```

- 关键词频次统计
- 年度分布热力图（最近 12 年）
- 词云生成（需 `wordcloud` 包）

#### F-4.2 主题建模 ✅

```
$ citationer text topics --method lda --num-topics 10
$ citationer text topics --method nmf
```

- LDA（gensim，含一致性分数）和 NMF（sklearn，TF-IDF）
- 自动确定最优主题数（上限 15）
- 主题-词汇分布 Rich 表格输出
- JSON 导出支持

#### F-4.3 中英文 NLP 处理 ✅

```
$ citationer text preprocess
$ citationer text preprocess --lang zh
$ citationer text preprocess --lang en
```

- 自动语言检测（CJK 汉字比例）
- 中文：jieba 分词 + 自定义词典 + 内置停用词表
- 英文：spaCy 词形还原（回退到正则分词）+ 内置停用词表
- 停用词文件：`data/stopwords_zh.txt`、`data/stopwords_en.txt`

#### F-4.4 文本聚类 ✅

```
$ citationer text cluster --method kmeans
$ citationer text cluster --method hierarchical
```

- K-Means / 层次聚类（AgglomerativeClustering）
- TF-IDF / SBERT（multilingual-MiniLM）向量化
- 轮廓系数评估、聚类规模与关键词展示
- CSV 导出支持

#### F-4.5 LLM 驱动的深度语义分析 ✅

```
$ citationer ai topics --auto-label         # 主题自动标注
$ citationer ai summarize                   # 文献综述生成
$ citationer ai trends                      # 研究趋势识别
$ citationer ai classify --dimensions methods,theories,applications  # 多维分类
$ citationer ai key-papers                  # 关键文献推荐
$ citationer ai info                        # LLM 配置状态与缓存统计
```

- 提供商：DeepSeek（默认）、OpenAI、Ollama，兼容任意 OpenAI API
- 隐私保护：`_sanitize_records()` 脱敏（去作者、机构、DOI）
- 缓存：SHA-256 哈希 → SQLite `llm_cache` 表
- 干运行模式：`--dry-run` 预览提示内容
- Token 用量追踪
- 输入上限 200K 字符（≈50K tokens），超出自动截断

#### F-4.6 传统摘要提取 ✅

```
$ citationer text summarize --max-sentences 10
```

- TF-IDF 关键句提取（无需 LLM，离线可用）
- 标题优先、摘要回退
- 输入上限 5000 句

---

### 4.5 研究脉络与趋势分析

#### F-5.1 研究热点演变（突发检测）✅

```
$ citationer trend hotspots --top 30
$ citationer trend hotspots --gamma 0.5      # 更敏感（检测弱突发）
$ citationer trend hotspots --min-years 3    # 最小持续年数
```

- 简化 Kleinberg 两状态自动机
- 突发强度排序、趋势方向标记（↗上升 / ↘下降）
- Gamma 灵敏度参数（0.5–2.0）

#### F-5.2 战略坐标图 ✅

```
$ citationer trend strategy --top 50
```

- 关键词共现 + Louvain 聚类
- 四象限：核心主题、专门化主题、新兴/衰退主题、基础主题
- 终端散点图（plotext）

#### F-5.3 主题河流图 ✅（轻量版）

```
$ citationer trend river --top 8 --window 5
```

- 滑动时间窗口（默认 5 年）
- 关键词占比矩阵 + Unicode 字符火花图
- 峰值、当前占比、趋势箭头

---

### 4.6 可视化输出

#### F-6.1 终端可视化 ✅

| 图表类型 | 命令 | 技术 |
|----------|------|------|
| Braille 折线图 | `stats yearly` | plotext |
| 双轴图（柱状+折线） | `stats yearly --cumulative` | plotext |
| Unicode 水平条形图 | `stats journals/authors/institutions` | 纯字符 █ |
| Rich 表格热力图 | `text keywords --per-year` | Rich |
| 终端散点图 | `trend strategy` | plotext |
| Unicode 火花图 | `trend river` | 纯字符 |

#### F-6.2 静态图表文件 ✅（引擎已有，CLI 部分接线）

| 图表类型 | 引擎函数 | CLI 接线 |
|----------|---------|----------|
| 年度发文折线图 (PNG/SVG) | `generate_yearly_chart()` | ✅ `stats yearly --save` |
| Top-N 柱状图 (PNG/SVG) | `generate_top_n_chart()` | ✅ `stats journals/authors --save` |
| 关键词词云 (PNG) | `generate_keyword_wordcloud()` | ✅ `text keywords --wordcloud` |
| 共现网络图 (HTML) | `NetworkEngine.to_html()` | ✅ `network --viz` |
| 战略坐标图 / 河流图 (PNG) | ❌ 未实现 | 🔜 |

#### F-6.3 HTML 交互式报告 ✅（基础版）

- 交互式 Plotly 网络图（弹簧布局 + 社区着色）
- 单文件 HTML，可独立部署
- 报告 HTML（`report quick -o r.html`，基础模板）
- 🔜 可折叠面板、搜索排序表格

---

### 4.7 报告生成

#### F-7.1 快速报告 ✅

```
$ citationer report quick -o report.md        # Markdown 格式
$ citationer report quick -o report.html      # HTML 格式
$ citationer report quick --enhance -o r.md   # LLM 增强（「研究发现与展望」章节）
```

- 自动整合 Overview、年度趋势、Top 期刊/作者/关键词、LDA 主题、关键词共现网络
- LLM 增强可选（需要配置 API Key），无 Key 时优雅降级
- 🟡 `--template` 参数接受但仅 `"academic"` 有效（`"simple"` 输出相同）

#### F-7.2 自定义报告 ✅

```
$ citationer report custom config.yaml -o report.md
```

- YAML 驱动：可配置标题和章节（overview / yearly / journals / authors / keywords / topics）
- 🟡 功能基础，尚不支持颜色方案、Logo 等高级定制

#### F-7.3 批量报告 🔜

```
$ citationer report batch --input-dirs dir1/ dir2/ dir3/
```

> 计划功能，未实现。需要对多个文献文件夹分别生成 + 对比报告。

---

### 4.8 CLI 交互设计

#### F-8.1 命令树（当前实际结构）✅

```
citationer                              # L1 自定义 Rich 全览
├── scan                               # 扫描目录（递归 + 自动识别）
├── status                             # 快速状态（非递归）
├── import                             # 导入题录到 SQLite
├── clean                              # 数据清洗与 4 层去重
├── stats                              # 描述性统计分析
│   ├── overview                       #   文献全景概览
│   ├── yearly                         #   年度趋势（终端图表 + PNG）
│   ├── journals                       #   期刊排名
│   ├── authors                        #   作者分析 + Price 定律
│   ├── institutions                   #   机构排名
│   └── citations                      #   引用分析
├── text                               # 文本挖掘与 NLP
│   ├── preprocess                     #   分词 + 语言检测
│   ├── keywords                       #   关键词频次 + 年度热力图 + 词云
│   ├── topics                         #   LDA/NMF 主题建模
│   ├── summarize                      #   TF-IDF 抽取式摘要
│   └── cluster                        #   K-Means / 层次聚类
├── network                            # 知识图谱与网络分析
│   ├── keywords                       #   关键词共现网络
│   ├── coauthors                      #   作者/机构合作网络 + 社区检测
│   ├── cocitation                     #   共被引分析
│   └── coupling                       #   文献耦合分析（关键词回退）
├── ai                                 # LLM 深度语义分析
│   ├── topics --auto-label            #   主题自动标注
│   ├── summarize                      #   文献综述生成
│   ├── trends                         #   研究趋势与空白识别
│   ├── classify                       #   多维分类
│   ├── key-papers                     #   关键文献推荐
│   └── info                           #   LLM 配置与缓存统计
├── trend                              # 趋势分析
│   ├── hotspots                       #   关键词突发检测
│   ├── strategy                       #   战略坐标图
│   └── river                          #   主题河流火花图
├── export                             # 数据导出
│   ├── csv / json / bibtex / ris / xlsx
├── report                             # 报告生成
│   ├── quick                          #   快速报告（MD/HTML）
│   └── custom                         #   自定义 YAML 报告
├── config                             # 配置管理
│   ├── show / set / init
├── interactive                        # 交互式向导（7 个主菜单项）
└── run                                # YAML 声明式流水线
```

#### F-8.2 Help 系统 ✅

三级体系均已实现：

| 级别 | 触发 | 内容 |
|------|------|------|
| L1 | `citationer --help` | Rich 自定义全览：快速开始 + 命令组概览 + 全局选项 |
| L2 | `citationer <group> --help` | rich-click 增强：子命令清单 + 用法示例 |
| L3 | `citationer <group> <cmd> --help` | rich-click 增强：完整参数表 + 示例 + 关联命令 |

#### F-8.3 交互模式 ✅

```
$ citationer interactive
```

- 7 个主菜单项：描述统计、文本分析、网络分析、趋势分析、扫描目录、导出数据、数据库管理
- Rich 交互式提示（`Prompt.ask`、`Confirm.ask`）
- 🟡 "保存为报告"功能待完善（当前显示占位提示）

#### F-8.4 声明式流水线 ✅

```
$ citationer run pipeline.yaml
```

- YAML 配置文件，支持 5 种动作类型：stats / text / network / trend / export
- 步骤间数据传递、错误处理（`on_error: stop`）
- 预置标准流水线模板（`examples/standard_pipeline.yaml`，10 个步骤）

---

## 5. 技术架构（实际）

### 5.1 技术栈

| 层次 | 技术 | 备注 |
|------|------|------|
| **语言** | Python 3.11+ | `pyproject.toml` 声明 `>=3.11` |
| **CLI 框架** | Typer + Rich + rich-click | 懒加载 14 个 CLI 模块，启动 ~150ms |
| **数据处理** | 标准库 + openpyxl + xlrd | 无 Pandas/Polars 依赖 |
| **中文分词** | jieba | 可选依赖（`[text]` 组） |
| **英文 NLP** | spaCy（回退正则） | 可选依赖 |
| **主题建模** | scikit-learn + gensim | 可选依赖（`[text]` 组） |
| **文本向量化** | sentence-transformers (SBERT) | 可选（聚类向量化备选） |
| **模糊匹配** | rapidfuzz（回退 difflib） | 去重引擎 |
| **网络分析** | networkx + python-louvain | 可选依赖（`[network]` 组） |
| **可视化（静态）** | matplotlib + wordcloud | 可选依赖（`[viz]` 组） |
| **可视化（终端）** | plotext | 可选依赖（`[viz]` 组） |
| **可视化（交互）** | plotly | 可选依赖（`[network]` 组） |
| **报告生成** | 自建 Markdown 拼接 | 无 Jinja2 依赖（简化实现） |
| **数据库** | SQLite（sqlite3，WAL 模式） | 7 张表 + 5 个索引 |
| **LLM 集成** | openai SDK（兼容 OpenAI API） | DeepSeek/OpenAI/Ollama |
| **配置管理** | YAML (PyYAML) + Pydantic | 环境变量覆盖 |
| **构建系统** | setuptools | `pyproject.toml` |
| **CI/CD** | GitHub Actions | Lint + Type Check + Test + PyPI 发布 |
| **包分发** | PyPI (pip/pipx) | `citationer` + `ctr` 别名 |

### 5.2 架构图（实际）

```
┌─────────────────────────────────────────────────────────┐
│                      CLI Layer                           │
│   main.py → 14 个命令模块（懒加载，~150ms 启动）          │
│   Typer + Rich + rich-click + plotext                   │
├─────────────────────────────────────────────────────────┤
│                   Analysis Layer                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │  Stats   │ │ Network  │ │  Text    │ │  Trend   │   │
│  │  Engine  │ │  Engine  │ │  Engine  │ │  Engine  │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│  ┌──────────┐ ┌──────────┐                              │
│  │ Dedup    │ │  LLM     │                              │
│  │ Engine   │ │  Client  │                              │
│  └──────────┘ └──────────┘                              │
├─────────────────────────────────────────────────────────┤
│                 Core / Data Layer                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐        │
│  │ 9 个     │ │ 4 层     │ │ 统一 Record 模型  │        │
│  │ Parser   │ │ 去重     │ │ (Pydantic,22字段) │        │
│  └──────────┘ └──────────┘ └──────────────────┘        │
├─────────────────────────────────────────────────────────┤
│                Persistence Layer                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐        │
│  │ SQLite   │ │ Config   │ │ Export / Report  │        │
│  │ (7表,5索)│ │ YAML     │ │ (5 格式 + MD/HTML)│       │
│  └──────────┘ └──────────┘ └──────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### 5.3 关键设计决策

- **懒加载 CLI 模块**：14 个命令文件按需导入，启动时间从 ~400ms 降至 ~150ms
- **插件化解析器**：`BaseParser`（ABC）→ `ParserRegistry`，按注册顺序 `detect()` 轮询
- **去重按年份分桶**：L2/L3 层按 `(年份, 作者)` 分桶，避免 O(n²)
- **批量 SQLite 操作**：导入 500 条/批，加载 4 个批量查询替代 3N+1
- **LLM 缓存**：SHA-256（提示 + 脱敏数据）→ SQLite，避免重复 API 调用
- **可选依赖分层**：text / network / ai / viz 四个可选组，核心功能零额外依赖

---

## 6. 发布与分发策略

### 6.1 当前渠道

| 渠道 | 状态 | 说明 |
|------|------|------|
| **PyPI (pip/pipx)** | ✅ 已发布 | `citationer` v4.0.4，CI 自动发布 |
| **GitHub Release** | ✅ 已配置 | tag `v*` 触发 PyPI 发布 |
| **PyInstaller** | 🟡 spec 已写，未构建 | `packaging/pyinstaller.spec` |
| **Docker** | ❌ | |
| **conda-forge** | ❌ | |

### 6.2 推荐安装方式

```bash
# 首选
pipx install citationer

# 备选
pip install citationer

# 全功能（含 NLP + 网络 + AI + 可视化）
pip install "citationer[all]"
```

### 6.3 命名空间

- PyPI 包名: `citationer`
- CLI 命令: `citationer`（简写别名 `ctr`）
- 命令前缀: `citationer`

---

## 7. 开发路线图

### Phase 1: MVP（最小可行产品）— ✅ 已完成（v1.x–v2.x）

> 2026-07-02 — 2026-07-03

- [x] 项目脚手架（setuptools, Typer, Rich, pytest）
- [x] CNKI Excel + WoS 纯文本/Excel（3 个解析器）
- [x] 统一 Pydantic 数据模型
- [x] 4 层去重引擎
- [x] `scan` / `status` / `import` / `clean` 命令
- [x] `stats overview` / `yearly` / `journals` / `authors` / `institutions`
- [x] 终端表格 + 图表输出
- [x] SQLite 缓存 + 批量提交
- [x] GitHub Actions CI + PyPI 发布

---

### Phase 2: 文本挖掘 + LLM + 网络分析 — ✅ 已完成（v2.1.9–v2.10.0）

> 2026-07-03 — 2026-07-05

- [x] jieba 中文分词 + spaCy 英文 NLP + 停用词表
- [x] 关键词频次统计 + 年代热力图
- [x] LDA/NMF 主题建模（自动最优主题数 + 一致性分数）
- [x] TF-IDF 关键句提取 + K-Means/层次聚类
- [x] LLM 多提供商客户端（DeepSeek/OpenAI/Ollama）
- [x] 6 个 AI 子命令（topics/summarize/trends/classify/key-papers/info）
- [x] LLM 数据脱敏 + SHA-256 缓存 + 干运行
- [x] 关键词共现网络 + 作者/机构合作网络
- [x] 共被引 & 文献耦合 + Plotly HTML 交互图
- [x] 多格式导出（CSV/GEXF/GraphML）
- [x] `text` / `network` / `ai` / `config` 命令组
- [x] 三级 Help 系统（L1 Rich 自定义 + L2/L3 rich-click）
- [x] 终端图表（plotext braille 折线 + Unicode 条形图）
- [x] 性能优化（懒加载、批量导入、rapidfuzz 预过滤、DB 批量加载）
- [x] `output/cls/` + `output/viz/` 目录自动创建

---

### Phase 3: 趋势分析与报告 — ✅ 已完成（v2.10.0–v3.0.0）

> 2026-07-05 — 2026-07-06

- [x] 关键词突变检测（简化 Kleinberg 算法，`trend hotspots`）
- [x] 战略坐标图（四象限主题定位，`trend strategy`）
- [x] 主题河流火花图（`trend river`）
- [x] 快速报告（Markdown/HTML，`report quick`）
- [x] 自定义 YAML 报告（`report custom`）
- [x] LLM 增强报告（`report quick --enhance`）

---

### Phase 4: 扩展与打磨 — ✅ 已完成（v4.1.0–v4.6.0）

> 目标：扩展解析器覆盖 + 提升工程质量，已于 v4.6.0 全部完成

#### 已完成

- [x] Scopus 解析器（CSV/Excel）
- [x] PubMed 解析器（XML + MEDLINE 双路径）
- [x] CSSCI 解析器（Excel/文本）
- [x] BibTeX 解析器
- [x] RIS 解析器
- [x] 交互模式（`citationer interactive`，7 菜单向导）
- [x] 声明式 YAML 流水线（`citationer run`）
- [x] 标准流水线模板（`examples/standard_pipeline.yaml`）
- [x] `export` 命令组（CSV/JSON/BibTeX/RIS/XLSX）
- [x] 基金/参考文献数据入库持久化
- [x] `ai key-papers` 子命令
- [x] P4-1 测试覆盖率提升至 ≥ 80%（v4.1.0）
- [x] P4-2 MkDocs 文档站点部署（v4.2.0）
- [x] P4-3 PyInstaller 二进制构建（v4.3.0）
- [x] P4-4 `stats funding` 子命令（v4.4.0）
- [x] P4-5 `report` 模板系统完善（v4.5.0）
- [x] P4-6 `interactive` 保存报告功能（v4.6.0）

---

### Phase 5: 高级功能与生态 — 🔜 计划中

> 持续迭代，按用户反馈驱动优先级

| # | 工作项 | 优先级 | 预估工作量 | 说明 |
|---|--------|--------|-----------|------|
| P5-1 | **多数据集对比分析** | ✅ 已完成 | 2–3 周 | 已实现 `compare` 命令组：overview / trends / topics / network；按 source_database / source_file 分组，输出 table/json/csv；已于 v5.0.0 发布 |
| P5-2 | **Web UI（`citationer serve`）** | 🟡 P1 | 3–4 周 | Flask/FastAPI 本地 Web 界面 + 交互式图表仪表盘 |
| P5-3 | **插件系统** | 🟢 P2 | 2–3 周 | 第三方贡献解析器；entry_points 发现 + 标准接口 |
| P5-4 | **PDF 全文分析** | 🟢 P2 | 3–4 周 | PDF 解析、全文主题建模、引文上下文分析 |
| P5-5 | **实时文献监控** | 🔵 P3 | 2–3 周 | RSS/API 追踪新增文献 + 邮件/终端通知 |
| P5-7 | **多语言国际化 (i18n)** | 🔵 P3 | 2 周 | gettext 或手动方案，中英文双语界面 |
| P5-8 | **EndNote / Zotero 解析器** | 🔵 P3 | 1 周 | EndNote XML + Zotero RDF/CSV |
| P5-10 | **数据库查询命令** (`citationer query`) | ✅ 已完成 | 1 周 | SQLite 直查或 DSL 过滤（按年份/期刊/作者/关键词筛选）；已于 v4.7.0 发布 |

> **下阶段重点**：P5-2（Web UI）为下一阶段重点。

### Phase 6: 愿景方向（远期）

> 不承诺排期，作为产品演进的方向参考

- **协作功能**：共享分析报告、团队文献库
- **引文网络**：前向引用追踪 + 引文级联分析
- **AI 深度分析**：多轮对话式文献探索、假设生成
- **期刊推荐**：基于手稿摘要推荐投稿目标期刊
- **学术社交图谱**：研究者合作关系发现 + 影响力分析

---

## 8. 当前质量指标与差距

### 8.1 测试覆盖率（2026-07-25 实测）

| 模块 | 覆盖率 | 状态 |
|------|--------|------|
| `llm/client.py` | 100% | ✅ |
| `models/record.py` | 100% | ✅ |
| `utils/database.py` | 100% | ✅ |
| `utils/serialization.py` | 100% | ✅ |
| `utils/date_utils.py` | 100% | ✅ |
| `analysis/stats.py` | 100% | ✅ |
| `cli/help.py` | 100% | ✅ |
| `cli/clean_cmd.py` | 98% | ✅ |
| `parsers/cssci.py` | 97% | ✅ |
| `parsers/scopus.py` | 97% | ✅ |
| `parsers/wos.py` | 96% | ✅ |
| `analysis/trend.py` | 96% | ✅ |
| `analysis/dedup.py` | 95% | ✅ |
| `utils/db_loader.py` | 94% | ✅ |
| `parsers/cnki.py` | 93% | ✅ |
| `parsers/pubmed.py` | 93% | ✅ |
| `analysis/network.py` | 93% | ✅ |
| `cli/scan_cmd.py` | 92% | ✅ |
| `cli/interactive_cmd.py` | 91% | ✅ |
| `cli/network_cmd.py` | 91% | ✅ |
| `cli/export_cmd.py` | 90% | ✅ |
| `cli/main.py` | 90% | ✅ |
| `viz/charts.py` | 89% | ✅ |
| `parsers/base.py` | 88% | ✅ |
| `utils/config.py` | 89% | ✅ |
| `parsers/ris.py` | 90% | ✅ |
| `cli/query_cmd.py` | 86% | ✅ |
| `cli/run_cmd.py` | 85% | ✅ |
| `cli/text_cmd.py` | 85% | ✅ |
| `analysis/text.py` | 84% | ✅ |
| `utils/query.py` | 83% | ✅ |
| `parsers/bibtex.py` | 82% | ✅ |
| `viz/terminal_charts.py` | 99% | ✅ |
| `cli/report_cmd.py` | 85% | ✅ |
| `cli/trend_cmd.py` | 99% | ✅ |
| `cli/stats_cmd.py` | 97% | ✅ |
| `cli/config_cmd.py` | 98% | ✅ |
| `cli/import_cmd.py` | 100% | ✅ |
| `cli/ai_cmd.py` | 94% | ✅ |
| **总计** | **93%** | ✅ 目标 80% 已达成 |

### 8.2 代码规模

| 指标 | 数值 |
|------|------|
| Python 源文件 | 28 个（`src/` 下） |
| 总代码行数 | ~5,650 行 |
| CLI 模块 | 15 个文件，~2,900 行 |
| 分析引擎 | 5 个文件 |
| 解析器 | 9 个类（8 个文件） |
| 测试文件 | 32 个，906 个测试 |
| 数据库表 | 7 张（含 5 个索引） |

### 8.3 已知技术债

| 项目 | 严重度 | 说明 |
|------|--------|------|
| `cli/interactive_cmd.py` 覆盖率低 | ✅ 已解决 | v4.9.0 已提升至 91% |
| `viz/terminal_charts.py` 覆盖率低 | ✅ 已解决 | v4.9.0 已提升至 99% |
| `parsers/scopus.py` / `parsers/cssci.py` 覆盖率 | ✅ 已解决 | v4.9.0 已提升至 97% / 97% |
| `cli/network_cmd.py` 覆盖率低 | ✅ 已解决 | v4.9.0 已提升至 91% |
| `llm/client.py` 覆盖率低 | ✅ 已解决 | v4.9.0 已提升至 100% |
| `cli/ai_cmd.py` / `cli/stats_cmd.py` / `cli/trend_cmd.py` / `cli/config_cmd.py` / `cli/import_cmd.py` 覆盖率低 | ✅ 已解决 | v4.10.0 已提升至 94% / 97% / 99% / 98% / 100% |
| 共享 test fixtures | ✅ 已解决 | `make_record` 已集中到 `tests/_factories`；DB seed 已提取到 `tests/_helpers` |
| `report` 模板系统 | ✅ 已解决 | `simple` / `academic` 模板已实现并测试 |
| `interactive` 保存报告 | ✅ 已解决 | v4.6.0 已实现 |
| 去重 L3 层 | ✅ 已解决 | v4.8.0 已支持 TTY 下人工确认，保留 `--non-interactive` 自动合并 |
| `stats funding` | ✅ 已解决 | v4.4.0 已实现 |
| WoS parser 覆盖率 | ✅ 已解决 | 已从 40% 提升至 96% |
| CI 覆盖率门禁 | ✅ 已解决 | `--cov-fail-under=80` 已启用 |
| CLI 层零测试 | ✅ 已解决 | 各 CLI 模块已有对应测试文件，整体 CLI 覆盖率达到 75%–100% |

---

## 9. 开放问题与决策记录

### Q1: 是否应该支持非题录的全文分析？— 已决策，延后

> **决策 (v1.0)**：MVP 阶段聚焦题录。Phase 5（P5-4）列入 PDF 全文分析，但不早于 Phase 4 质量达标。

### Q2: 是否需要 GUI？— 已决策，列入 Phase 5

> **决策 (v1.0)**：纯 CLI 优先。Phase 5（P5-2）列入 Web UI（`citationer serve`），作为 HTML 交互报告的升级路径。

### Q3: 多语言文献混合分析策略？— ✅ 已实现

> **决策 (v2.0)**：自动检测语言，中文 jieba 分词、英文 spaCy 处理。中英文关键词取并集参与后续分析。

### Q4: LLM 集成的范围和时机？— ✅ 已实现并扩展

> **决策 (v2.0 → v4.0)**：Phase 2 引入 DeepSeek API，后续扩展为多提供商（OpenAI/Ollama 兼容）。已实现脱敏 + 缓存 + 干运行 + Token 追踪。本地 Ollama 支持已在 v3.x 加入。

### Q5: 配置文件是否要支持声明式分析流水线？— ✅ 已实现

> **决策 (v2.0)**：`citationer run pipeline.yaml` 已实现，支持 5 种动作类型。

### Q6: 数据集大小的上限？— 当前经验值

> **当前状态**：1k–10k 记录流畅。SQLite + 批量提交架构可支撑到 50k。十万级以上需性能优化（分块处理、并行化、Polars 替代）。

### Q7: 是否要提供 API/Python SDK？— 仍待决策

> **当前建议**：内部模块可导入但不承诺稳定 API。CLI 稳定后再考虑正式 Python SDK。

### Q8: 测试覆盖率目标？— 新决策

> **决策 (v3.0)**：Phase 4 目标 ≥ 80%。优先覆盖 CLI 集成测试（端到端场景）、trend/viz/report 单元测试。CI 中加入覆盖率门禁（≥ 80% 红线）。

### Q9: 文档策略？— 新决策

> **决策 (v3.0)**：采用 MkDocs Material 主题部署 GitHub Pages。wiki/ 目录保留为同步源（GitHub Wiki 镜像），`site/` 为文档站点源。两者保持同步。

### Q10: 发布渠道优先级？— 更新

> **决策 (v3.0)**：维持 PyPI 为主渠道。Phase 4 补齐 PyInstaller 二进制分发。Docker 和 conda-forge 降为 Phase 5 P3。Homebrew 不做。

---

## 附录 A: 竞品与参考

| 工具 | 类型 | 特点 | 与 citationer 的差异 |
|------|------|------|---------------------|
| **CiteSpace** | GUI (Java) | 强大的科学知识图谱 | 学习曲线陡，GUI 操作，不适合快速探索 |
| **VOSviewer** | GUI (Java) | 出色的共现网络可视化 | 仅网络图，无统计报告 |
| **Bibliometrix (R包)** | R 包 | 文献计量全流程 | 需 R 环境，编程门槛较高 |
| **Publish or Perish** | GUI | 引用指标计算 | 依赖 Google Scholar API |
| **Litmaps / Connected Papers** | Web | 文献发现与关联 | 在线服务，数据需上传 |
| **citationer** | CLI | 本地、快速、一键式 | 🎯 填补「终端优先」的空白 |

---

## 附录 B: 版本历史

| 版本 | 日期 | 主要内容 |
|------|------|---------|
| **PRD v1.0** | 2026-07-02 | Phase 1 MVP 原始需求定义 |
| **PRD v2.0** | 2026-07-03 | Phase 2–5 完整规划：Text NLP、LLM、Network、Trend、Report、Help 系统 |
| **PRD v2.1** | 2026-07-04 | 终端统计图表（plotext braille line + hbar） |
| **PRD v3.0** | 2026-07-09 | 整合前三版，反映 v4.0.4 实际状态，重构 Phase 4–5 待办，新增质量指标与架构审计 |
| **Release v4.10.0** | 2026-07-25 | 最终 CLI 覆盖率推进：ai/stats/trend/config/import 全部 ≥85%；项目覆盖率 ~93% |
| **Release v4.9.0** | 2026-07-25 | 技术债清零：提升 interactive/terminal/network/llm/scopus/cssci 测试覆盖率；修复 Scopus/CSSCI 解析细节 |
| **Release v4.8.0** | 2026-07-24 | 去重 L3 人工确认、共享 fixtures、WoS 覆盖率 96%、PRD 刷新 |

---

> 📝 **下一版迭代建议**:
> 1. P4-1 测试覆盖率 — 最关键的工程质量债
> 2. P4-2 文档站点部署 — 降低新用户上手门槛
> 3. P4-4 + P4-5 + P4-6 功能补齐 — 低成本的体验提升
> 4. Phase 5 按 GitHub Issues 用户反馈驱动，避免过度设计
