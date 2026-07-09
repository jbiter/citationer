# Citationer v3 — User Handbook

> **A terminal-first bibliometric analysis CLI tool** — from raw export files to insights.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Installation](#2-installation)
3. [Quick Start](#3-quick-start)
4. [Data Management](#4-data-management)
5. [Descriptive Statistics](#5-descriptive-statistics)
6. [Text Mining & NLP](#6-text-mining--nlp)
7. [Network Analysis](#7-network-analysis)
8. [LLM-Powered AI Analysis](#8-llm-powered-ai-analysis)
9. [Configuration](#9-configuration)
10. [Trend Analysis](#10-trend-analysis)
11. [Report Generation](#11-report-generation)
12. [Export & Interoperability](#12-export--interoperability)
13. [Supported Formats](#13-supported-formats)
14. [Help System](#14-help-system)

---

## 1. Overview

**Citationer** is a terminal-first bibliometric analysis tool for researchers, students, and librarians. It automates the entire pipeline:

```
Raw export files  →  Parse & Unify  →  Clean & Dedup  →  Analyze  →  Export
```

### Architecture

```
┌─────────────────────────────────────────┐
│              CLI Layer (Typer + Rich)    │
├─────────────────────────────────────────┤
│  Stats Engine  │  Text Engine  │  Network Engine
├─────────────────────────────────────────┤
│  Parsers (CNKI, WoS)  │  Dedup Engine   │
├─────────────────────────────────────────┤
│  SQLite Cache  │  Config (YAML)  │  LLM Client
└─────────────────────────────────────────┘
```

### Key Design Principles

- **Zero-config**: Auto-detects file formats; defaults cover 80% of use cases
- **Local-first**: All data processed locally; LLM calls are opt-in with privacy safeguards
- **Pipe-friendly**: JSON, CSV, GEXF, GraphML export — works with standard Unix tools
- **Progressive complexity**: Simple commands for common tasks; sub-commands for deep analysis

---

## 2. Installation

### Requirements

- Python 3.11 or later
- pip or pipx

### Quick Install

```bash
pipx install citationer          # Recommended (isolated)
pip install citationer           # Standard pip install
```

### Full Install (all optional features)

```bash
pip install "citationer[all]"
```

This installs:
- `jieba` — Chinese text segmentation
- `scikit-learn`, `gensim` — Topic modeling & clustering
- `networkx`, `python-louvain`, `plotly` — Network analysis & visualization
- `openai` — LLM API client
- `wordcloud` — Word cloud generation

### Verify Installation

```bash
citationer --help
```

---

## 3. Quick Start

A minimal workflow takes 4 commands:

```bash
cd /path/to/your/literature     # 1. Go to your data directory
citationer scan                 # 2. Detect bibliographic files
citationer import               # 3. Parse & store records
citationer stats overview       # 4. View the dashboard
```

### Expected Output

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

## 4. Data Management

### `scan` — Detect bibliographic files

Scans a directory recursively for supported file types, auto-identifies the source database and format.

```bash
citationer scan                  # Current directory
citationer scan /path/to/data    # Specific directory
citationer scan --no-recursive   # Top-level only
```

**Output**: A table showing filename, detected source, record count, and year range per file.

### `status` — Quick check

A faster, non-recursive version of `scan`.

```bash
citationer status
```

### `import` — Parse & store records

Parses detected files and stores unified records in a local SQLite database (`.citationer/cache.db`).

```bash
citationer import                         # Import — clears old data by default
citationer import file1.txt file2.xlsx    # Import specific files
citationer import --keep                  # Append to existing data
```

### `clean` — Validate & deduplicate

Runs data quality checks and a 4-layer deduplication engine.

```bash
citationer clean                          # Full clean: validate + dedup
citationer clean --no-check-duplicates    # Validate only
citationer clean --no-check-missing       # Dedup only
citationer clean --dry-run                # Preview without merging
```

**Deduplication Layers**:

| Layer | Method | Action |
|-------|--------|--------|
| 1 | DOI exact match | Auto-merge |
| 2 | Title similarity ≥ 85% + same year | Auto-merge |
| 3 | Title similarity ≥ 70% + same first author + same year | Auto-merge (log for review) |
| 4 | Cross-language: author surname + year + journal + pages | Auto-merge |

**Validation Checks**:
- Missing title / year / authors
- Year anomalies (outside 1900–2030 range)

---

## 5. Descriptive Statistics

All stats commands read from the local database. Run `citationer import` first.

### `stats overview` — Dashboard

```bash
citationer stats overview
```

**Output**: Total records, year range, journal count, unique authors, solo/coop rates, institution/country counts, language distribution, document type distribution, average citations, h-index.

### `stats yearly` — Publication trends

```bash
citationer stats yearly                  # Annual counts
citationer stats yearly --cumulative     # With cumulative line
```

Includes a linear trend slope (publications/year).

### `stats journals` — Journal rankings

```bash
citationer stats journals --top 20       # Top-20 journals by count
```

### `stats authors` — Author analysis

```bash
citationer stats authors --top 20        # Top-20 authors
```

**Additional metrics**:
- **Price's Law core authors**: `count ≥ 0.749 × √(max_publications)`
- **Author h-index**: Based on citations within the dataset
- **Solo/coop rates**: Percentages of single-author vs. multi-author works
- **First-author distribution**: Who publishes most as first author

### `stats institutions` — Institution rankings

```bash
citationer stats institutions --top 20   # Top-20 institutions
```

---

## 6. Text Mining & NLP

### `text preprocess` — Tokenization

Auto-detects language (Chinese vs. English), tokenizes, removes stop words.

```bash
citationer text preprocess               # All fields (title + abstract)
citationer text preprocess --field title # Title only
citationer text preprocess --lang zh     # Force Chinese tokenization
citationer text preprocess --lang en     # Force English tokenization
citationer text preprocess --top 10      # Show top 10 samples
```

**Chinese**: jieba segmentation with bundled academic stop words (~250 terms).
**English**: Built-in regex tokenizer with lemmatization; spaCy used if available (`en_core_web_sm`).

### `text keywords` — Frequency analysis

```bash
citationer text keywords --top 50        # Top-50 keywords
citationer text keywords --min-count 3   # Filter rare keywords
citationer text keywords --per-year      # With year × keyword heatmap
citationer text keywords --format json --output keywords.json
```

### `text topics` — Topic modeling

```bash
citationer text topics --method lda      # LDA (gensim)
citationer text topics --method nmf      # NMF (scikit-learn)
citationer text topics --num-topics 8    # Specify topic count
citationer text topics --max-terms 15    # Terms per topic
```

**Auto-detection**: When `--num-topics` is not specified, the engine automatically determines an optimal count based on vocabulary size (capped at 15).
**Coherence score**: LDA reports `c_v` coherence for quality assessment.

### `text summarize` — Extractive summary

TF-IDF based key sentence extraction — no LLM required, works offline.

```bash
citationer text summarize --max-sentences 10
citataioner text summarize --output summary.txt
```

### `text cluster` — Document clustering

Clusters papers by title + abstract similarity.

```bash
citationer text cluster --method kmeans       # K-Means (default)
citationer text cluster --method hierarchical # Agglomerative
citationer text cluster --n-clusters 5        # Specify cluster count
citationer text cluster --vectorizer tfidf     # TF-IDF (default)
citationer text cluster --output clusters.csv
```

Reports silhouette score, cluster sizes, and representative terms per cluster.

---

## 7. Network Analysis

All network commands support CSV, GEXF, and GraphML export, plus interactive HTML visualization via Plotly.

### `network keywords` — Co-occurrence network

```bash
citationer network keywords --top 50 --threshold 3
citationer network keywords --output-format gexf --output keywords.gexf
citationer network keywords --viz --output network.html
```

**Parameters**:
- `--top N`: Only include top-N most frequent keywords
- `--threshold N`: Minimum co-occurrence count for an edge

### `network coauthors` — Collaboration network

```bash
# Author collaboration
citationer network coauthors --min-papers 2
citationer network coauthors --min-papers 5 --output-format csv

# Institution collaboration
citationer network coauthors --type institutions --min-papers 3
citationer network coauthors --type institutions --viz --output inst_net.html
```

Includes **Louvain community detection** — nodes are color-coded by community in HTML exports.

### `network cocitation` — Co-citation analysis

Two references cited together in the same paper form a co-citation link. Requires the `references` field to be populated (included in WoS full-record exports; not available in CNKI exports).

```bash
citationer network cocitation --top 30
```

### `network coupling` — Bibliographic coupling

Two papers that share references are coupled. Falls back to keyword-based coupling if reference data is unavailable.

```bash
citationer network coupling --top 30
citationer network coupling --output-format gexf --viz
```

### Export Formats

| Format | Use Case |
|--------|----------|
| `csv` | Edge list for spreadsheet analysis |
| `gexf` | Import into Gephi |
| `graphml` | Import into Cytoscape |
| `html` (via `--viz`) | Interactive Plotly force-directed graph, self-contained single file |

---

## 8. LLM-Powered AI Analysis

Requires an LLM API key. See [Configuration](#9-configuration) for setup.

### Privacy Design

Only **titles and abstracts** are sent to the LLM. Author names, emails, affiliations, DOIs, and source filenames are **stripped** before transmission. All responses are cached locally by input hash to avoid redundant API calls.

### `ai topics` — Topic labeling

Runs LDA topic modeling locally, then sends the topic keywords to the LLM for human-readable labels.

```bash
citationer ai topics --auto-label --num-topics 5
citationer ai topics --auto-label --dry-run   # Preview without API call
```

**Important**: Only topic keywords are sent to the LLM — not the full paper records. This keeps token consumption minimal (~500-1000 tokens per call).

### `ai summarize` — Literature review generation

Generates a 200–500 word literature review summary from titles and abstracts.

```bash
citationer ai summarize                     # Default: first 100 records
citationer ai summarize --max-records 50    # Limit input size
citationer ai summarize --language zh       # Output in Chinese
citationer ai summarize --dry-run           # Preview the prompt
```

### `ai trends` — Trend identification

Compares early vs. recent periods to identify shifting research focuses, emerging topics, and declining areas.

```bash
citationer ai trends
citationer ai trends --window 5             # 5-year comparison window
citationer ai trends --dry-run
```

### `ai classify` — Multi-dimensional classification

Classifies papers across configurable dimensions (research methods, theoretical frameworks, application domains, etc.).

```bash
citationer ai classify
citationer ai classify --dimensions "methods,theories,applications"
citationer ai classify --dry-run
```

### `ai info` — LLM status

```bash
citationer ai info
```

Shows: API key status (masked), model, endpoint, temperature, max tokens, cache statistics.

### Token Budget Protection

The LLM client enforces a default **200,000 character** input limit (~50K tokens). If your data exceeds this, records are automatically truncated with a note. Use `--max-records` to explicitly control input size. The `ai topics` command sends only topic keywords (0 records), so it never hits the limit.

---

## 9. Configuration

### Config File

Citationer stores configuration in `.citationer/config.yaml` (auto-created in the current directory).

### CLI Commands

```bash
citationer config show                          # View all settings
citationer config set llm.api_key sk-xxx        # Set API key
citationer config set llm.model deepseek-chat   # Set model
citationer config set llm.base_url https://api.openai.com/v1  # Set endpoint
citationer config set llm.temperature 0.5       # Set temperature
citationer config set llm.max_tokens 8192       # Set max output tokens
citationer config init                          # Create config with defaults
citationer config init --force                  # Overwrite existing config
```

### All Configurable LLM Keys

| Key | Description | Default |
|-----|-------------|---------|
| `llm.api_key` | API key (required) | `""` |
| `llm.model` | Model name | `deepseek-chat` |
| `llm.base_url` | API endpoint URL | `https://api.deepseek.com` |
| `llm.temperature` | Generation temperature (0.0–2.0) | `0.3` |
| `llm.max_tokens` | Max output tokens | `4096` |

### Environment Variables (override config file)

| Variable | Overrides |
|----------|----------|
| `CITATIONER_LLM_API_KEY` | `llm.api_key` |
| `CITATIONER_LLM_MODEL` | `llm.model` |
| `CITATIONER_LLM_BASE_URL` | `llm.base_url` |
| `CITATIONER_LLM_TEMPERATURE` | `llm.temperature` |
| `CITATIONER_LLM_MAX_TOKENS` | `llm.max_tokens` |
| `DEEPSEEK_API_KEY` | `llm.api_key` (legacy, lower priority) |

### Priority

```
Environment variable  >  Config file (.citationer/config.yaml)  >  Default
```

### Provider Examples

```bash
# DeepSeek (default)
citationer config set llm.base_url https://api.deepseek.com
citationer config set llm.model deepseek-chat

# OpenAI
citationer config set llm.base_url https://api.openai.com/v1
citationer config set llm.model gpt-4o

# Ollama (local)
citationer config set llm.base_url http://localhost:11434/v1
citationer config set llm.model llama3
citationer config set llm.api_key ollama    # Ollama doesn't require a real key
```

---

## 10. Trend Analysis

### `trend hotspots` — Keyword burst detection

Identifies keywords that suddenly spike in frequency, revealing emerging research topics.

```bash
citationer trend hotspots --top 30        # Top-30 keywords
citationer trend hotspots --gamma 0.5     # More sensitive (detects weaker bursts)
citationer trend hotspots --min-years 3   # Min 3 consecutive years
```

**Parameters**:
- `--top N`: Number of top keywords to analyze (default 30)
- `--gamma`: Sensitivity (0.5 = sensitive, 2.0 = only strong bursts)
- `--min-years`: Minimum consecutive years to qualify as a burst

**Output**: Table of detected bursts with keyword, time period, strength, and trend direction (📈 rising / 📉 declining).

### `trend strategy` — Strategic diagram

Builds a keyword co-occurrence network, detects theme clusters, and plots them on a centrality × density quadrant diagram.

```bash
citationer trend strategy --top 50        # Top-50 keywords
```

**Quadrants**:
| Quadrant | Name | Meaning |
|----------|------|---------|
| Q1 (high C, high D) | 🚀 Motor | Well-developed, central themes |
| Q2 (low C, high D) | 🔬 Niche | Well-developed, peripheral themes |
| Q3 (low C, low D) | 🌱 Emerging | Under-developed, weak connections |
| Q4 (high C, low D) | 📚 Basic | Important but under-developed |

**Output**: Table of themes with centrality/density scores + terminal scatter plot.

---

---

## 11. Report Generation

### `report quick` — Quick report

Generates a comprehensive Markdown or HTML report including all analysis results.

```bash
citationer report quick -o report.md       # Markdown report
citationer report quick -o report.html     # HTML report
citationer report quick --enhance -o r.md  # LLM-enhanced with AI findings
```

**Report contents**: Overview, yearly trend, top journals/authors, keywords, topic modeling, co-occurrence network.

### `report custom` — Custom report

Generate a report using a YAML configuration file.

```bash
citationer report custom config.yaml -o report.md
```

**Example config.yaml**:
```yaml
title: "My Literature Analysis"
sections:
  - overview
  - yearly
  - journals
  - authors
  - keywords
  - topics
```

---

## 12. Export & Interoperability

### Network Export Formats

| Command | Flag | Output |
|---------|------|--------|
| `network keywords` | `--output-format csv` | Edge list CSV |
| `network keywords` | `--output-format gexf` | Gephi-compatible GEXF |
| `network keywords` | `--output-format graphml` | Cytoscape-compatible GraphML |
| `network keywords` | `--viz` | Interactive Plotly HTML |
| `network coauthors` | `--viz` | Community-colored HTML graph |

### Text Analysis Export

```bash
citationer text keywords --format json --output keywords.json
citationer text topics --output topics.json
citationer text cluster --output clusters.csv
```

### Pipe-friendly Output

All table-formatted output can be combined with standard Unix tools:

```bash
citationer stats journals --top 30 | grep "Nature"
citationer text keywords --format json | jq '.keywords[:5]'
```

---

## 13. Supported Formats

| Source | Format | Extension | Parser | Status |
|--------|--------|-----------|--------|--------|
| Web of Science | Plain text (tagged) | `.txt`, `.ciw` | `WosTextParser` | ✅ |
| Web of Science | Tab-delimited | `.txt`, `.tsv`, `.csv` | `WosTabDelimitedParser` | ✅ |
| Web of Science | Excel export | `.xlsx`, `.xls` | `WosExcelParser` | ✅ |
| CNKI (知网) | Excel export | `.xlsx` | `CnkiExcelParser` | ✅ |
| Scopus | CSV/Excel | `.csv`, `.xlsx` | — | 🔜 Phase 3 |
| PubMed | XML/MEDLINE | `.xml`, `.nbib` | — | 🔜 Phase 3 |
| BibTeX | Generic | `.bib` | — | 🔜 Phase 3 |
| RIS | Generic | `.ris` | — | 🔜 Phase 3 |

### File Naming for CNKI Detection

CNKI Excel exports are identified by characteristic Chinese column headers (题名, 作者, 来源, 关键词, 摘要, etc.). At least 3 matching headers are required for positive detection.

### File Naming for WoS Detection

- **Tagged text**: First line starts with `FN ` or a valid WoS field tag (`PT `, `AU `, etc.)
- **Tab-delimited**: First line contains tab-separated field tags (`PT\tAU\tTI\t...`)
- **Excel**: Header row contains English markers like "Publication Type", "Authors", "Article Title"

---

## 14. Help System

Citationer has a three-tier help system:

### L1 — Overview (`citationer --help`)

Shows all top-level commands grouped by category, plus quick-start examples and global options.

```bash
citationer --help
citationer              # Same effect (no-args = help)
```

### L2 — Command Group (`citationer <group> --help`)

Shows all sub-commands within a group with descriptions.

```bash
citationer stats --help
citationer network --help
citationer ai --help
```

### L3 — Command Detail (`citationer <group> <cmd> --help`)

Shows full parameter list with types, defaults, and usage examples.

```bash
citationer stats yearly --help
citationer text topics --help
citationer network keywords --help
```

---

## Appendix: Data Directory Structure

```
your-project/
├── data/                       # Your bibliographic files
│   ├── wos_export.txt
│   └── cnki_2024.xlsx
├── .citationer/                # Auto-generated (gitignore this)
│   ├── cache.db                # SQLite database
│   ├── cache.db-shm            # SQLite WAL
│   ├── cache.db-wal            # SQLite WAL
│   └── config.yaml             # Your configuration
└── citationer_output/          # Default report output directory
```

---

*Citationer v3 — July 2026*
