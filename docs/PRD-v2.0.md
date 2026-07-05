# Citationer — 文献题录分析工具 · 产品需求文档 v2.0

> **状态**: Phase 2 开发中  
> **作者**: Jason  
> **日期**: 2026-07-02  
> **更新**: 2026-07-03 — 新增 F-8.2 Help 系统设计，更新命令树  
> **许可证**: MIT · 开源项目  
> **仓库**: github.com/JasonCENG/citationer  

---

## 目录

1. [产品愿景与定位](#1-产品愿景与定位)
2. [目标用户](#2-目标用户)
3. [核心概念](#3-核心概念)
4. [功能需求](#4-功能需求)
   - [4.1 数据摄入与解析](#41-数据摄入与解析)
   - [4.2 描述性统计分析](#42-描述性统计分析)
   - [4.3 知识图谱与网络分析](#43-知识图谱与网络分析)
   - [4.4 语义分析与文本挖掘](#44-语义分析与文本挖掘)
   - [4.5 研究脉络与趋势分析](#45-研究脉络与趋势分析)
   - [4.6 可视化输出](#46-可视化输出)
   - [4.7 报告生成](#47-报告生成)
   - [4.8 CLI 交互设计](#48-cli-交互设计)
5. [技术架构](#5-技术架构)
6. [发布与分发策略](#6-发布与分发策略)
7. [开发路线图](#7-开发路线图)
8. [开放问题与待讨论](#8-开放问题与待讨论)

---

## 1. 产品愿景与定位

### 一句话描述

> **`citationer`** —— 一键式文献题录分析 CLI 工具。进入包含题录文件的目录，运行一条命令，即可获得从描述统计到主题挖掘的完整文献分析报告。

### 定位

一个面向科研工作者（研究生、教师、科研人员）的**轻量级、本地化、零配置**文献分析工具。它不替代 CiteSpace、VOSviewer 等专业 GUI 工具，而是提供一种「终端优先」的快速分析体验——适合在日常工作流中快速了解一个文献集合的全貌，或在论文写作初期快速生成统计图表和趋势分析。

### 核心设计原则

| 原则 | 说明 |
|------|------|
| **开箱即用** | 自动检测目录下的题录文件，无需手动指定格式，智能推断 |
| **零配置分析** | 默认行为覆盖 80% 的常见分析需求，高级用户可自定义配置 |
| **本地优先** | 所有题录数据在本地处理；LLM 功能使用 DeepSeek API，摘要文本经用户确认后发送，敏感数据可配置脱敏 |
| **管道友好** | 输出结果可被 `grep`、`jq` 等标准 Unix 工具进一步处理 |
| **渐进复杂度** | 简单的事情简单做，复杂分析通过子命令暴露 |
| **AI 增强** | 集成 DeepSeek 大模型进行语义理解、主题标注、综述生成等高级分析，作为传统 NLP 方法的增强层 |

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
│   ├── cache.db             # 解析后的统一数据
│   ├── config.yaml          # 用户自定义配置
│   └── reports/             # 生成的报告输出
└── citationer_output/       # 默认报告输出目录
```

### 3.3 支持的题录格式

| 来源 | 格式 | 扩展名 | 优先级 |
|------|------|--------|--------|
| **CNKI（知网）** | Excel 导出 | `.xlsx` | P0 |
| **Web of Science** | 纯文本/制表符分隔 | `.txt`, `.ciw` | P0 |
| **Web of Science** | Excel 导出 | `.xlsx` | P0 |
| **Scopus** | CSV/Excel 导出 | `.csv`, `.xlsx` | P1 |
| **PubMed** | XML/MEDLINE | `.xml`, `.nbib` | P1 |
| **CSSCI** | 文本/Excel | `.txt`, `.xlsx` | P1 |
| **通用 BibTeX** | BibTeX | `.bib` | P1 |
| **通用 RIS** | RIS | `.ris` | P1 |
| **EndNote** | EndNote XML | `.xml` | P2 |
| **Zotero** | RDF/CSV | `.rdf`, `.csv` | P2 |

---

## 4. 功能需求

### 4.1 数据摄入与解析

#### F-1.1 自动扫描与格式检测

```
$ citationer scan
# 或进入目录后直接运行
$ cd /path/to/literature && citationer status
```

**需求**:
- 递归或非递归扫描当前目录下的题录文件
- 自动识别文件格式和来源（基于文件头、字段特征）
- 输出扫描结果表格（文件名、格式、条目数、年份范围）
- 对无法识别的文件给出提示

**示例输出**:
```
📁 扫描结果: /home/user/thesis-literature/
┌──────────────────────┬──────────┬────────┬──────────────┐
│ 文件名               │ 来源     │ 条目数 │ 年份范围     │
├──────────────────────┼──────────┼────────┼──────────────┤
│ cnki_ai_research.xlsx│ CNKI     │ 234    │ 2018 - 2025  │
│ wos_core.txt         │ WoS Core │ 156    │ 2015 - 2024  │
│ scopus_search.csv    │ Scopus   │ 89     │ 2020 - 2025  │
│ unknown.csv          │ ❓ 未知  │ -      │ -            │
└──────────────────────┴──────────┴────────┴──────────────┘
总计: 479 条记录, 3 个来源
```

#### F-1.2 数据导入与合并

```
$ citationer import          # 导入所有检测到的文件
$ citationer import cnki_ai_research.xlsx wos_core.txt
```

**需求**:
- 将不同来源的题录数据解析为统一内部格式
- 字段映射（例如 CNKI 的「机构」映射到统一 `affiliation` 字段）
- 处理编码问题（UTF-8/GBK/GB2312 自动检测）
- 中文作者姓名处理（姓氏在前/在后归一化）

**严格的去重策略**（保证数据干净可信）:
- **DOI 精确去重** (Layer 1): 两条记录 DOI 完全一致 → 自动合并
- **标题模糊去重** (Layer 2): 标题相似度 ≥ 85%（基于编辑距离 + 余弦相似度双验证）+ 年份一致 → 标记为疑似重复，自动合并
- **标题+第一作者去重** (Layer 3): 标题相似度 ≥ 70% + 第一作者相同 + 年份相同 → 标记为疑似重复，需人工确认
- **中英文标题交叉去重** (Layer 4): 对于 CNKI（中文标题）与 WoS（英文标题）同一文献的场景，通过 DOI 优先匹配；无 DOI 时，检查作者+年份+期刊+卷期页码组合
- 合并策略: 字段取并集（CNKI 补充中文关键词，WoS 补充英文摘要和引用数据）

#### F-1.3 数据导出

```
$ citationer export --format csv          # 导出合并后的数据
$ citationer export --format bibtex       # 导出 BibTeX
$ citationer export --format excel        # 导出Excel（带统计sheet）
```

**需求**:
- 支持导出为 CSV, JSON, BibTeX, RIS, Excel
- 可选择导出字段子集
- 支持按来源、年份等条件筛选导出

#### F-1.4 数据校验与清洗

```
$ citationer clean --check-duplicates --check-missing
```

**需求**:
- 检测并报告缺失关键字段的记录（缺标题、缺年份、缺作者）
- 重复检测：基于 DOI、标题相似度、标题+第一作者
- 交互式或批量去重
- 年份异常检测（如 202 代替 2020）
- 作者名格式统一（全大写转首字母大写等）

---

### 4.2 描述性统计分析

#### F-2.1 概览仪表盘

```
$ citationer stats overview
```

**需求** — 输出一个「文献全景」摘要:
- 总文献数、去重后文献数
- 覆盖年份范围
- 来源数（期刊数、会议数等）
- 作者总数（独著率、合作率）
- 机构数
- 涉及国家/地区数
- 语言分布
- 文献类型分布（期刊论文/会议论文/学位论文/综述/...）
- 平均引用次数、h-index

#### F-2.2 时间维度分析

```
$ citationer stats yearly              # 年度发表趋势
$ citationer stats yearly --cumulative # 累积发表量
$ citationer stats monthly             # 月度趋势（适用于时间跨度较小的情况）
```

**需求**:
- 按年份/月份统计发表数量
- 支持分组对比（按来源、按期刊、按机构）
- 趋势线拟合（线性/多项式）
- 预测未来 1-2 年的发表趋势
- 识别发表高峰期

#### F-2.3 期刊/来源分析

```
$ citationer stats journals --top 20
```

**需求**:
- Top-N 期刊（按发文量）
- 期刊影响因子分布（如果有来源数据）
- 核心期刊占比（如北大核心、CSSCI、SCI分区）
- 期刊集中度分析（Bradford 定律分区）
- 期刊共现分析（哪些期刊常被一起引用）

#### F-2.4 作者分析

```
$ citationer stats authors --top 20
```

**需求**:
- Top-N 高产作者
- 作者发文年份分布
- 独著 vs 合著比例
- 平均合作者人数趋势
- 第一作者 vs 通讯作者统计
- Price 定律：核心作者识别（发文量 ≥ 0.749 × sqrt(最高产作者发文量)）
- 作者 h-index（基于数据集内引用）

#### F-2.5 机构分析

```
$ citationer stats institutions --top 20
```

**需求**:
- Top-N 高产机构
- 机构类型分布（高校/科研院所/医院/企业）
- 机构地域分布（省份/城市/国家）
- 机构合作网络
- 机构发文趋势（各机构的时间维度展开）

#### F-2.6 基金资助分析

```
$ citationer stats funding
```

**需求**:
- 基金资助率（有标注基金 vs 无标注）
- Top-N 基金来源（国家自然科学基金、国家重点研发计划等）
- 基金资助趋势

#### F-2.7 引用分析（需题录包含引用数据）

```
$ citationer stats citations
```

**需求**:
- 引用分布（均值、中位数、分布直方图）
- 高被引论文 Top-N
- 引用年份分布
- 自引率估算

---

### 4.3 知识图谱与网络分析

#### F-3.1 关键词共现网络

```
$ citationer network keywords --top 50 --threshold 3
```

**需求**:
- 构建关键词共现矩阵
- 导出为 GEXF / GraphML / CSV（可用 Gephi/Cytoscape 打开）
- 直接在终端展示简化版网络（或生成 HTML 交互图）
- 关键词聚类（Community Detection — Louvain 算法）
- 中心性指标：度中心性、中介中心性、接近中心性

#### F-3.2 合作网络

```
$ citationer network coauthors --min-papers 2
```

**需求**:
- 作者合作网络
- 机构合作网络
- 国家/地区合作网络
- 识别关键节点（桥接不同合作群体的研究者）

#### F-3.3 共被引与文献耦合

```
$ citationer network cocitation --top 30
$ citationer network coupling --top 30
```

**需求**:
- 共被引分析（两篇文献同时被第三篇引用）
- 文献耦合分析（两篇文献有共同参考文献）
- 识别知识基础（被引最多的参考文献群）

---

### 4.4 语义分析与文本挖掘

#### F-4.1 关键词分析

```
$ citationer text keywords --top 30
```

**需求**:
- 关键词频次统计（作者关键词 + 数据库补充关键词）
- 关键词年代分布热力图
- 关键词突变检测（Kleinberg's Burst Detection Algorithm）
- 关键词云图生成

#### F-4.2 主题建模

```
$ citationer text topics --method lda --num-topics 10
$ citationer text topics --method nmf --num-topics 8
```

**需求**:
- LDA (Latent Dirichlet Allocation) 主题建模
- NMF (Non-negative Matrix Factorization) 主题建模
- 自动确定最优主题数（基于困惑度/一致性分数）
- 主题-词汇分布输出
- 主题-文档分布输出
- 主题随时间的演化（Dynamic Topic Model）

#### F-4.3 中文与英文 NLP 处理 (同时支持)

```
$ citationer text preprocess          # 自动检测语言并同时处理中英文
$ citationer text preprocess --lang zh    # 仅中文
$ citationer text preprocess --lang en    # 仅英文
```

**需求**:
- **语言自动检测**: 基于标题+摘要自动判断文献语言，中英文文献混合数据集自动分流处理
- **中文**: jieba 分词 + 自定义词典（学术术语）+ 停用词表
- **英文**: spaCy 分词 + 词形还原 + n-gram 提取
- **中英文结果融合**: 中文关键词保留原文，英文关键词翻译对照（可选），统一参与后续主题建模和聚类
- **自定义词典支持**（用户可添加领域专业术语）
- **内置中英文停用词表** (学术文献专用，包含常见学术短语)

#### F-4.4 文本相似度与聚类

```
$ citationer text cluster --method hierarchical
```

**需求**:
- 基于标题+摘要的 TF-IDF / Word2Vec / Sentence-BERT 向量化
- 层次聚类 / K-Means 聚类
- 聚类结果可视化（树状图/散点图）
- 识别离群文献

#### F-4.5 LLM 驱动的深度语义分析 🆕 (DeepSeek)

```
$ citationer ai topics --auto-label     # LLM 为主题自动生成人类可读标签
$ citationer ai summarize               # LLM 生成文献集合综述摘要
$ citationer ai trends                  # LLM 识别研究趋势和空白
$ citationer ai classify                # LLM 对文献进行多维分类
```

**需求**:
- **LLM 提供商**: DeepSeek 开放平台 API (deepseek-chat / deepseek-reasoner)
- **API Key 管理**: 支持环境变量 `DEEPSEEK_API_KEY` 和配置文件两种方式

**核心功能**:
- **主题标注** (auto-label): LDA/NMF 生成的主题词交给 LLM，返回人类可读的主题标签（如 "deep learning in medical imaging"）
- **综述生成** (summarize): 基于所有文献的标题+摘要，生成 200-500 字的文献集合综述
- **趋势识别** (trends): LLM 从时间维度分析研究焦点的转移，识别新兴方向和研究空白
- **多维分类** (classify): 按研究方法、理论框架、应用领域等维度自动分类文献
- **关键文献推荐** (key-papers): LLM 基于语义理解识别该领域的奠基性文献和最新突破文献

**隐私与成本控制**:
- 仅上传标题+摘要（脱敏后），不上传作者、机构等身份信息
- 批量请求合并，减少 API 调用次数
- 结果缓存（相同输入不重复请求）
- 显示每次调用的 token 消耗
- 支持 `--dry-run` 预览将发送给 LLM 的内容

#### F-4.6 传统摘要提取与文献速览

```
$ citationer text summarize --top 10
```

**需求**:
- 基于 TF-IDF 的关键句提取（各文献摘要的核心句）
- 轻量级方法，无需 LLM API，适合离线环境

---

### 4.5 研究脉络与趋势分析

#### F-5.1 研究热点演变

```
$ citationer trend hotspots --window 3
```

**需求**:
- 基于时间窗口的关键词/主题热度变化
- 上升趋势词（热度持续增长）
- 下降趋势词（热度持续衰减）
- 新兴词（近期突然出现的关键词）
- 稳定词（长期保持高热度的关键词）

#### F-5.2 战略坐标图 (Strategic Diagram)

```
$ citationer trend strategic-diagram
```

**需求**:
- 基于关键词共现聚类
- X轴：向心度（Centraility）—— 与其他主题的联系强度
- Y轴：密度（Density）—— 主题内部词之间的联系强度
- 四象限：主流主题、边缘主题、新兴/衰退主题、核心/基础主题

#### F-5.3 主题河流图 (Thematic River / Alluvial)

```
$ citationer trend river --num-topics 8
```

**需求**:
- 随时间变化的主题强度河流图
- 展示主题的合并、分裂、兴起、消亡

---

### 4.6 可视化输出

#### F-6.1 终端可视化 ✅ 已实现

- [x] Rich 表格（彩色、可排序）
- [x] 终端折线图（plotext braille 字符，`stats yearly`）
- [x] 终端柱状图/条形图（Unicode █ 字符，`stats journals/authors/institutions`）
- [x] 终端热力图（Rich 表格版，`text keywords --per-year`）

#### F-6.2 静态图表文件 ⚠️ 代码已有，CLI 未接线

| 图表类型 | 状态 | 说明 |
|----------|------|------|
| 年度发文折线图 (PNG/SVG) | ⚠️ | `viz/charts.py` 已有，CLI 无 flag |
| 期刊/机构/作者柱状图 (PNG/SVG) | ⚠️ | 同上 |
| 关键词词云 (PNG) | ⚠️ | `generate_keyword_wordcloud()` 已有，CLI 无 flag |
| 共现网络图 (HTML) | ✅ | `network --viz` 生成 Plotly HTML |
| 战略坐标图、河流图、桑基图 | 🔜 | Phase 3 |

#### F-6.3 HTML 交互式报告 ✅ 已实现

- [x] 交互式 Plotly 网络图（`network --viz`）
- [x] 可独立部署（单文件 HTML）
- [ ] 可折叠面板、搜索排序表格 → Phase 3 report 命令

---

### 4.7 报告生成

#### F-7.1 快速报告

```
$ citationer report quick        # 一键生成完整报告
$ citationer report quick --template academic  # 学术风模板
```

**需求**:
- 预设报告模板（学术论文风、PPT汇报风、简洁风）
- 自动包含所有基础统计 + 可视化图表
- 输出格式: Markdown / HTML / PDF（通过 pandoc/weasyprint）

#### F-7.2 自定义报告

```
$ citationer report custom --config report.yaml
```

**需求**:
- 通过 YAML/TOML 配置文件定义报告内容和样式
- 可选择包含/排除特定分析模块
- 自定义图表颜色方案
- 自定义标题、副标题、机构 Logo

#### F-7.3 批量报告

```
$ citationer report batch --input-dirs dir1/ dir2/ dir3/
```

**需求**:
- 对多个文献文件夹分别生成报告
- 生成对比分析报告（跨数据集比较）

---

### 4.8 CLI 交互设计

#### F-8.1 命令结构 (Phase 2 现状)

```
citationer
├── scan                  # 扫描目录，识别题录文件
├── status                # 快速查看当前目录状态（简化版 scan）
├── import                # 导入题录文件到数据库
├── clean                 # 数据清洗与去重
├── stats                 # 描述性统计分析
│   ├── overview          #   文献全景概览
│   ├── yearly            #   年度发表趋势
│   ├── journals          #   期刊/来源分析
│   ├── authors           #   作者分析
│   └── institutions      #   机构分析
├── text                  # 文本挖掘与 NLP
│   ├── preprocess        #   分词 + 语言检测 + 停用词
│   ├── keywords          #   关键词频次统计 + 年代热力图
│   ├── topics            #   LDA / NMF 主题建模
│   ├── summarize         #   TF-IDF 关键句提取
│   └── cluster           #   K-Means / 层次聚类
├── network               # 知识图谱与网络分析
│   ├── keywords          #   关键词共现网络
│   ├── coauthors         #   作者/机构合作网络
│   ├── cocitation        #   共被引分析
│   └── coupling          #   文献耦合分析
├── ai                    # LLM 驱动的深度语义分析
│   ├── topics            #   主题自动标注 (auto-label)
│   ├── summarize         #   文献综述生成
│   ├── trends            #   研究趋势识别
│   ├── classify          #   多维分类
│   └── info              #   LLM 配置状态与缓存统计
├── config                # 配置管理
│   ├── show              #   查看当前配置
│   ├── set               #   设置配置项
│   └── init              #   初始化配置文件
├── export                # 导出数据 (Phase 3)
├── trend                 # 趋势分析 (Phase 3)
└── report                # 报告生成 (Phase 3)
```

#### F-8.2 Help 系统设计 🆕 (v2.0 新增)

> **设计目标**: 打造层次清晰、信息密度递进的帮助系统，让新用户快速上手、老用户精准查找。终端优先，兼顾美观与实用。

##### F-8.2.1 三级 Help 体系

```
L1: citationer --help               → 全览：所有一级命令 + 命令组概览 + 全局选项
L2: citationer <group> --help        → 聚焦：该命令组下所有子命令 + 用法示例
L3: citationer <group> <cmd> --help  → 详情：单个命令的完整参数说明 + 使用示例
```

##### F-8.2.2 L1 — 全览 (`citationer --help`)

**触发**: `citationer`（无参数）或 `citationer --help`

**内容布局**:

```
┌─────────────────────────────────────────────────────────────┐
│  📚 Citationer — 一键式文献题录分析 CLI 工具  v1.1.0          │
├─────────────────────────────────────────────────────────────┤
│  快速开始:                                                   │
│    $ cd /path/to/literature                                 │
│    $ citationer scan           # 扫描题录文件                 │
│    $ citationer import         # 导入数据                    │
│    $ citationer stats overview # 查看概览                    │
│                                                             │
├─ 📁 数据管理 ───────────────────────────────────────────────┤
│  scan        扫描目录，自动识别格式和来源                      │
│  status      快速查看当前目录状态（简化版 scan）              │
│  import      导入题录文件到本地 SQLite 数据库                 │
│  clean       数据清洗：缺失字段检测、异常值检测、智能去重      │
│                                                             │
├─ 📊 分析引擎 ───────────────────────────────────────────────┤
│  stats       描述统计 (overview, yearly, journals, …)        │
│  text        文本挖掘 (preprocess, keywords, topics, …)      │
│  network     网络分析 (keywords, coauthors, cocitation, …)   │
│  ai          LLM 语义分析 (summarize, trends, classify, …)  │
│                                                             │
├─ ⚙ 工具与配置 ──────────────────────────────────────────────┤
│  config      管理 LLM 和其他配置项 (show, set, init)          │
│                                                             │
├─ 🌐 全局选项 ───────────────────────────────────────────────┤
│  --verbose, -v     详细输出（调试模式）                       │
│  --quiet, -q       安静模式（仅输出结果数据）                  │
│  --output, -o PATH 指定输出目录                               │
│  --no-color        禁用彩色输出                               │
│  --help, -h        显示帮助信息                               │
│                                                             │
│  使用 citationer <command> --help 查看子命令详情              │
└─────────────────────────────────────────────────────────────┘
```

**设计要点**:
- **分区展示**: 按功能域分组（数据管理/分析引擎/工具配置），降低认知负载
- **概要描述**: 每个命令一行说明 + 关键子命令（括号内）
- **快速开始**: 顶部 3-4 条命令覆盖最短路径，新用户 30 秒内跑通
- **版本号**: 顶部显示，方便排查问题

##### F-8.2.3 L2 — 命令组聚焦 (`citationer <group> --help`)

**触发**: `citationer stats --help`、`citationer text --help` 等

**内容布局** (以 `stats` 为例):

```
┌─────────────────────────────────────────────────────────────┐
│  📊 stats — 描述性统计分析                                   │
│  对已导入的文献题录数据执行各类描述统计。                      │
│  使用前请先运行 citationer import 导入数据。                  │
├─────────────────────────────────────────────────────────────┤
│  子命令:                                                    │
│    overview        文献全景概览：总量、年份、作者、机构、      │
│                    h-index、文献类型与语言分布                 │
│    yearly          年度发表趋势：发表量、累积量、趋势拟合      │
│                    选项: --cumulative                        │
│    journals        期刊分析：Top-N 高产期刊排名               │
│                    选项: --top N (默认 20)                    │
│    authors         作者分析：高产作者、Price 核心作者、        │
│                    独著/合著率、h-index                       │
│                    选项: --top N (默认 20)                    │
│    institutions    机构分析：Top-N 高产机构排名               │
│                    选项: --top N (默认 20)                    │
│                                                             │
├─ 用法 ──────────────────────────────────────────────────────┤
│  $ citationer stats overview                                │
│  $ citationer stats yearly --cumulative                     │
│  $ citationer stats journals --top 10                       │
│                                                             │
│  使用 citationer stats <subcommand> --help 查看详细参数       │
└─────────────────────────────────────────────────────────────┘
```

**设计要点**:
- **前置条件**: 顶部提示是否需要先运行其他命令
- **子命令清单**: 每个子命令一段描述 + 关键选项
- **用法示例**: 底部 3-4 个最常用命令

##### F-8.2.4 L3 — 命令详情 (`citationer <group> <cmd> --help`)

**触发**: `citationer stats yearly --help` 等

**内容布局** (以 `stats yearly` 为例):

```
┌─────────────────────────────────────────────────────────────┐
│  citationer stats yearly — 年度发表趋势分析                   │
│  按年份统计文献发表数量，支持累积量展示和趋势线拟合。          │
├─────────────────────────────────────────────────────────────┤
│  参数:                                                      │
│    --cumulative, -c   显示累积发表量 (默认: false)            │
│                       类型: bool                             │
│                                                             │
├─ 示例 ──────────────────────────────────────────────────────┤
│  $ citationer stats yearly                                  │
│  $ citationer stats yearly --cumulative                     │
│  $ citationer stats yearly -o result.json --format json     │
│                                                             │
├─ 相关命令 ──────────────────────────────────────────────────┤
│  citationer stats overview  查看整体统计概览                 │
│  citationer trend hotspots  研究热点演变分析 (Phase 3)       │
└─────────────────────────────────────────────────────────────┘
```

**设计要点**:
- **完整参数表**: 选项名、短选项、类型、默认值、说明
- **实际示例**: 覆盖基本用法和组合用法
- **相关命令**: 底部引导用户发现关联功能

##### F-8.2.5 技术实现方案

| 组件 | 技术 | 说明 |
|------|------|------|
| CLI 框架 | Typer | 内置 Click `--help`，支持覆盖 |
| Rich 增强 | `rich-click` | 替换默认 help 为 Rich 面板/表格/分组渲染 |
| L1 定制 | 自定义 click.Command 或 app.callback | 精细排版超越默认布局 |
| 多语言 | gettext 或手动 | 预留中英文双语 help 接口 |

**最小实现路径** (Phase 2 可交付):
1. 安装 `rich-click`，Typer 的 `--help` 自动获得 Rich 渲染
2. 确保每个 `@app.command()` 的 docstring 和参数 `help=` 描述完整
3. L1 全览通过自定义 callback 覆盖

##### F-8.2.6 设计原则

| 原则 | 说明 |
|------|------|
| **渐进式信息披露** | L1→L2→L3 信息密度递增，按需深入 |
| **示例驱动** | 每级 help 包含可复制粘贴的实际命令 |
| **功能域分组** | L1 按业务域分区，非字母排序 |
| **终端优先** | 适配标准 80 列终端 |
| **相关推荐** | L3 底部推荐关联命令，引导功能发现 |

#### F-8.3 交互模式 (Phase 4)

```
$ citationer interactive
```

**需求**:
- 向导式分析流程（引导用户选择分析步骤）
- 每个步骤展示进度条（rich.progress）
- 支持在交互模式中随时导出中间结果

#### F-8.4 全局选项

```
--verbose, -v      详细输出（调试模式）
--quiet, -q        安静模式（仅输出结果数据）
--output, -o PATH  指定输出目录
--config, -c PATH  指定配置文件路径
--no-color         禁用彩色输出
--help, -h         显示帮助信息
```

---

## 5. 技术架构

### 5.1 技术选型建议

| 层次 | 技术 | 理由 |
|------|------|------|
| **语言** | Python 3.10+ | 数据处理和 NLP 生态最成熟 |
| **CLI 框架** | Typer + Rich | 类型安全、自动补全、美观的终端输出 |
| **数据处理** | Pandas + Polars | 高效的数据清洗和统计 |
| **中文分词** | jieba + pkuseg | 成熟稳定，可自定义词典 |
| **英文 NLP** | spaCy | 工业级 NLP pipeline |
| **主题建模** | scikit-learn + gensim | LDA/NMF 标准实现 |
| **文本向量化** | sentence-transformers | SBERT 等多语言模型 |
| **网络分析** | networkx + python-igraph | 共现/合作网络构建与分析 |
| **社区检测** | python-louvain | Louvain 算法 |
| **突变检测** | 自实现 Kleinberg 算法 | 逻辑不复杂，可控性好 |
| **可视化（静态）** | matplotlib + seaborn + wordcloud | 标准方案 |
| **可视化（交互）** | plotly + pyecharts | HTML 交互图表 |
| **报告生成** | Jinja2 + Markdown + pandoc | 模板化报告 |
| **数据解析** | openpyxl + pandas + bibtexparser | 多格式题录解析 |
| **缓存/数据库** | SQLite (via sqlite3) | 轻量、零配置、便携 |
| **LLM 集成** | DeepSeek API (openai SDK 兼容) | 主题标注、综述生成、趋势识别 |
| **配置管理** | YAML (PyYAML) + pydantic | 类型安全的配置校验 |
| **打包分发** | Poetry + PyInstaller / pip | 见第6节 |
| **CI/CD** | GitHub Actions | 代码检查、测试、发布 PyPI |
| **版本管理** | Git + GitHub (公开仓库) | MIT 开源许可证 |

### 5.2 架构图（概念）

```
┌─────────────────────────────────────────────────┐
│                   CLI Layer                      │
│          (Typer + Rich, 命令路由)                │
├─────────────────────────────────────────────────┤
│                Analysis Layer                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │  Stats   │ │ Network  │ │  Text/Semantic   │ │
│  │  Engine  │ │  Engine  │ │     Engine       │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
├─────────────────────────────────────────────────┤
│              Core / Data Layer                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │  Parser  │ │  Merger  │ │  Unified Model   │ │
│  │ (CNKI,   │ │  Dedup   │ │  (Pydantic       │ │
│  │  WoS,...)│ │  Clean   │ │   Schema)        │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
├─────────────────────────────────────────────────┤
│             Persistence Layer                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │  SQLite  │ │  Config  │ │  Export / Report │ │
│  │  Cache   │ │  YAML    │ │  (Jinja2/Plotly) │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
└─────────────────────────────────────────────────┘
```

### 5.3 关键设计决策

#### 插件化解析器

每个数据源（CNKI、WoS、Scopus...）作为一个解析器插件，便于社区贡献新的数据源支持：

```python
# 伪代码
class BaseParser(ABC):
    @abstractmethod
    def detect(self, filepath: Path) -> bool: ...
    @abstractmethod
    def parse(self, filepath: Path) -> list[Record]: ...
    @property
    @abstractmethod
    def source_name(self) -> str: ...
```

#### 统一数据模型

```python
class Record(BaseModel):
    title: str
    title_en: Optional[str]
    authors: list[Author]
    year: Optional[int]
    journal: Optional[str]
    volume: Optional[str]
    issue: Optional[str]
    pages: Optional[str]
    doi: Optional[str]
    abstract: Optional[str]
    abstract_en: Optional[str]
    keywords: list[str]
    keywords_en: Optional[list[str]]
    institutions: list[Institution]
    funding: Optional[list[str]]
    doc_type: Optional[str]       # article, review, conference, ...
    language: Optional[str]
    citation_count: Optional[int]
    references: Optional[list[str]]
    source_database: str          # CNKI, WoS, Scopus...
    source_file: str              # 原始文件名
    raw_data: dict                # 保留原始字段
```

---

## 6. 发布与分发策略

### 6.1 渠道分析

| 渠道 | 优势 | 劣势 | 用户群 |
|------|------|------|--------|
| **pip (PyPI)** | Python 生态标准，跨平台，自动依赖管理 | 需要 Python 环境 | 🏆 **首选** — 科研用户基本都有 Python |
| **Homebrew** | macOS 一站式安装 | 仅 macOS，打包门槛高 | 补充渠道 — macOS 便捷安装 |
| **pipx** | 隔离安装 CLI 工具的最佳实践 | 需要 Python + pipx | 推荐安装方式 |
| **APT/RPM** | Linux 原生体验 | 维护成本高，需多发行版适配 | 后续考虑 |
| **Docker** | 零环境依赖 | 镜像体积大 | 特殊场景（服务器批量分析） |
| **conda** | 科学生态 | 需 conda 环境 | 可考虑 conda-forge |
| **独立二进制 (PyInstaller)** | 单文件，无需 Python | 体积大，无法 pip 升级 | GitHub Release 附带 |

### 6.2 推荐策略

```
优先级 1: pip / pipx（PyPI 包）
  └── $ pipx install citationer
  └── $ pip install citationer

优先级 2: Homebrew（macOS）
  └── $ brew install citationer

优先级 3: GitHub Release
  └── 预编译二进制文件 (PyInstaller)
  └── Docker 镜像

优先级 4（后期）: conda-forge, APT/RPM
```

### 6.3 项目名与命名空间

- PyPI 包名: `citationer`
- CLI 命令: `citationer`（支持 `ct` 作为简写别名）
- Homebrew formula: `citationer`
- GitHub: `github.com/<user>/citationer`

---

## 7. 开发路线图

### Phase 1: MVP（最小可行产品）— ✅ 已完成

**目标**: 解析 CNKI + WoS 数据，完成基础描述统计，在终端输出，搭建 CI/CD

- [x] 项目脚手架搭建（setuptools, Typer, Rich, pytest）
- [x] CNKI Excel 格式解析器
- [x] WoS 纯文本/制表符分隔/Excel 格式解析器
- [x] 统一数据模型 (Pydantic)
- [x] 严格去重引擎 (DOI + 标题模糊 + 标题+作者 + 跨语言)
- [x] `scan` / `status` 命令（扫描目录）
- [x] `import` 命令（导入数据）
- [x] `clean` 命令（清洗/去重，含 --cache 清缓存）
- [x] `stats overview` / `stats yearly` / `stats journals` / `stats authors` / `stats institutions`
- [x] 终端表格输出（Rich Tables）+ 终端图表（plotext braille 折线 + Unicode 条形图）
- [x] PNG 图表导出（matplotlib: 年度趋势、Top-N 柱状图）— 代码有，CLI 未接线
- [x] `.citationer/` 缓存机制 (SQLite + 批量提交优化)
- [x] GitHub Actions CI (lint + test)
- [x] PyPI 发布（自动从 GitHub Release 触发）

### Phase 2: 文本挖掘 + LLM + 网络分析 — 进行中

- [x] 中文分词 (jieba) + 英文 NLP（内置停用词表，spaCy 可选）
- [x] 内置中英文学术语停用词表
- [x] 关键词频次统计 + 年代热力图
- [x] LDA / NMF 主题建模（自动最优主题数 + 一致性分数）
- [x] TF-IDF 关键句提取 (text summarize)
- [x] K-Means / 层次聚类 (text cluster)
- [x] LLM 客户端：DeepSeek/OpenAI/Ollama 多提供商支持
- [x] LLM 主题自动标注 (ai topics --auto-label)
- [x] LLM 文献综述生成 (ai summarize)
- [x] LLM 趋势识别 (ai trends)
- [x] LLM 多维分类 (ai classify)
- [x] 数据脱敏与结果缓存 (ai 全部命令)
- [x] 关键词共现网络 + CSV/GEXF/GraphML 导出
- [x] 作者/机构合作网络 + Louvain 社区检测
- [x] 共被引 & 文献耦合分析
- [x] HTML 交互式网络图 (Plotly)
- [x] `text` / `network` / `ai` / `config` 命令组
- [x] CLI 配置管理 (config show/set/init)
- [x] LLM 多提供商可配置 (api_key/model/base_url/temperature/max_tokens)
- [x] Help 系统完善 (rich-click 集成，L1/L2/L3 三级 help，自定义 L1 布局)
- [x] `--version` 命令
- [x] `output/` 目录自动创建 (cls/ + viz/)
- [x] 性能优化：import 批量提交 (50× 加速)、去重 quick_ratio 预过滤、stats 单次遍历、DB 批量加载、spaCy 缓存
- [x] 图标风格统一

#### Phase 2 收尾工作（2026-07-05）

以下为 PRD 与实现之间的差距，需在 Phase 2 正式收尾前完成：

| # | 工作项 | 来源 | 说明 |
|---|--------|------|------|
| 1 | **PNG/SVG 图表导出接 CLI** | F-6.2 + Phase 1 | `viz/charts.py` 已有 `generate_yearly_chart()` / `generate_top_n_chart()` / `generate_keyword_wordcloud()`，但 stats 命令没有 flag 来触发。需在 `stats yearly` / `stats journals` / `stats authors` 增加 `--save-png` / `--save-svg` 选项 |
| 2 | **词云暴露给 CLI** | F-6.2 | `text keywords` 增加 `--wordcloud` flag，将关键词生成词云 PNG 保存到 `output/viz/` |
| 3 | **关键词年代热力图** | Phase 3 | `text keywords --per-year` 已有表格版热力图，可考虑 plotext 热力图或保存为 PNG |
| 4 | **`export` 命令** | F-1.3 | 数据导出（CSV/JSON/BibTeX/RIS/Excel）— 目前仅 clean --save 支持 CSV，需独立命令 |
| 5 | **`config` 初始化体验** | F-8.1 | 首次运行 `ai` 命令时自动提示配置 API Key |

### Phase 3: 趋势分析与报告 — 预计 3-4 周

- [ ] 关键词年代热力图
- [ ] 突变检测（Burst Detection）
- [ ] 战略坐标图
- [ ] 主题河流图
- [ ] `trend` 命令组
- [ ] `report quick` 报告生成（Markdown / HTML / PDF）
- [ ] Jinja2 报告模板（学术风 / PPT风 / 简洁风）
- [ ] LLM 增强报告（生成「研究发现与展望」章节）

### Phase 4: 扩展与打磨 — 预计 4-6 周

- [ ] Scopus 解析器
- [ ] PubMed 解析器
- [ ] CSSCI 解析器
- [ ] BibTeX / RIS 通用格式解析器
- [ ] 交互模式 (`citationer interactive`)
- [ ] 自定义配置文件与声明式分析流水线
- [ ] Homebrew formula
- [ ] 用户文档网站 (MkDocs / VitePress)
- [ ] 单元测试覆盖率 ≥ 80%
- [ ] 预编译二进制文件 (PyInstaller)

### Phase 5: 高级功能与生态 — 持续迭代

- [ ] 插件系统（第三方贡献解析器）
- [ ] Web UI（`citationer serve` 启动本地 Web 界面）
- [ ] 多数据集对比分析
- [ ] 实时文献监控（RSS/API 追踪新增文献）
- [ ] 本地 LLM 支持 (Ollama) 作为 DeepSeek 的离线替代
- [ ] conda-forge 发布
- [ ] 多语言界面国际化

---

## 8. 开放问题与待讨论

### Q1: 是否应该支持非题录的全文分析？

> **当前建议**: MVP 阶段聚焦题录（标题、摘要、关键词、作者、机构等元数据），不处理全文 PDF。全文分析（PDF 解析、全文主题建模、引文上下文分析）留到后续版本。但可以在数据模型中预留扩展空间。

### Q2: 是否需要 GUI？

> **当前建议**: MVP 阶段纯 CLI。后续可考虑添加 `citationer serve` 命令启动本地 Web 界面。也可以考虑输出 HTML 交互报告作为「GUI」的替代方案。

### Q3: 多语言文献混合分析策略？ ✅ 已决策

> **决策**: Phase 2 同时支持中英文 NLP pipeline。自动检测文献语言，中文用 jieba 分词，英文用 spaCy 处理。中英文关键词取并集参与后续分析。翻译对齐作为未来可选项。

### Q4: LLM 集成的范围和时机？ ✅ 已决策

> **决策**: Phase 2 即引入 LLM，使用 DeepSeek 开放平台 API。
> - 提供 `citationer ai` 子命令组
> - API Key 通过环境变量 `DEEPSEEK_API_KEY` 管理
> - 仅上传脱敏后的标题+摘要，不上传作者/机构等身份信息
> - 结果缓存避免重复请求
> - 后续 Phase 5 增加本地 LLM (Ollama) 支持作为离线替代方案

### Q5: 配置文件是否要支持声明式分析流水线？ ✅ 已决策

> **当前建议**: 支持。用户在 `.citationer/config.yaml` 中可以定义分析流水线：
> ```yaml
> pipeline:
>   - scan
>   - import
>   - clean
>   - stats:
>       - overview
>       - yearly
>       - journals: {top: 20}
>   - text:
>       - topics: {num_topics: 10}
>   - report: {template: academic}
> ```
> 一键运行 `citationer run` 即可执行完整流程。

### Q6: 数据集大小的上限？

> **当前建议**: 在本地 SQLite + Pandas 架构下，万级别（10k-50k）的题录数据应流畅运行。十万级以上需考虑性能优化（分块处理、并行化、Polars 替代 Pandas 等）。MVP 以 1k-10k 数据规模为优化目标。

### Q7: 是否要提供 API/Python SDK？

> **当前建议**: 内部模块设计为可导入，但不承诺稳定的 Python API。用户可 `from citationer import ...` 但标注为不稳定接口。当 CLI 稳定后，再考虑发布正式 Python SDK。

---

## 附录 A: 竞品与参考

| 工具 | 类型 | 特点 | 与 citationer 的差异 |
|------|------|------|---------------------|
| **CiteSpace** | GUI (Java) | 强大的科学知识图谱 | 学习曲线陡，GUI操作，不适合快速探索 |
| **VOSviewer** | GUI (Java) | 出色的共现网络可视化 | 仅网络图，无统计报告 |
| **Bibliometrix (R包)** | R 包 | 文献计量全流程 | 需 R 环境，编程门槛较高 |
| **CiteSpace 的 BibExcel** | GUI (Win) | 文献计量预处理 | 仅 Windows |
| **HistCite** | GUI | 引文脉络分析 | 停更多年 |
| **Publish or Perish** | GUI | 引用指标计算 | 依赖 Google Scholar API |
| **Litmaps / Connected Papers** | Web | 文献发现与关联 | 在线服务，数据需上传 |
| **citationer** | CLI | 本地、快速、一键式 | 🎯 填补「终端优先」的空白 |

---

## 附录 B: 命名 brainstorming

当前项目名: **citationer**（citation + -er，意为「做引文分析的人/工具」）

备选:
- `litana` — literature + analysis
- `biblic` — bibliography + cli
- `litstat` — literature statistics
- `scilit` — science + literature
- `citekit` — citation + toolkit

> **建议保留 citationer**，简洁且含义明确，PyPI 上目前（2026-07）似乎未被占用。

---

## 附录 C: 项目管理与基础设施

### 开源策略

- **许可证**: MIT — 最宽松的开源许可证，最大化社区采用率
- **代码仓库**: GitHub (github.com/JasonCENG/citationer) — 公开仓库
- **贡献指南**: `CONTRIBUTING.md` 包含解析器插件开发指南
- **行为准则**: Contributor Covenant

### CI/CD 流水线 (GitHub Actions)

```yaml
# 触发条件
- push/PR to main 分支 → lint + test (Python 3.10/3.11/3.12)
- GitHub Release 发布 → 自动构建并发布 PyPI
- 定期 (weekly) → 依赖安全检查 (Dependabot)
```

**流水线阶段**:

| 阶段 | 工具 | 说明 |
|------|------|------|
| **Lint** | ruff | 代码风格与静态检查 |
| **Type Check** | mypy | 类型检查 |
| **Test** | pytest + coverage | 单元测试 + 覆盖率报告 |
| **Build** | Poetry build | 构建 wheel + sdist |
| **Publish** | PyPI trusted publishing | 从 GitHub Release 自动发布 PyPI |
| **Docs** | MkDocs (GitHub Pages) | 文档自动构建与部署 |

### 项目文件结构

```
citationer/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml              # Lint + Test
│   │   └── publish.yml         # PyPI 发布
│   └── dependabot.yml
├── src/
│   └── citationer/
│       ├── __init__.py
│       ├── cli/                 # CLI 命令定义 (Typer)
│       ├── parsers/             # 题录解析器 (CNKI, WoS, ...)
│       ├── models/              # Pydantic 数据模型
│       ├── analysis/            # 分析引擎 (stats, network, text, trend)
│       ├── llm/                 # LLM 集成 (DeepSeek client)
│       ├── viz/                 # 可视化 (matplotlib, plotly)
│       ├── report/              # 报告生成 (Jinja2)
│       └── utils/               # 工具函数
├── tests/
├── docs/
├── prd/
├── pyproject.toml
├── LICENSE
├── README.md
└── CONTRIBUTING.md
```

---

> 📝 **下一步**:
> 1. ~~讨论并确认功能优先级~~ ✅ 已完成
> 2. ~~确定 Phase 1 MVP 的具体范围~~ ✅ 已完成
> 3. 创建 GitHub 公开仓库并初始化项目结构
> 4. 搭建 Python 项目脚手架 (Poetry + Typer + Rich)
> 5. 实现 CNKI + WoS 解析器原型
> 6. 配置 GitHub Actions CI/CD
> 7. 开始 Phase 1 开发
