# Citationer

> **One-click bibliometric analysis CLI tool** — scan, import, analyze, and visualize your literature collection in the terminal.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/citationer.svg)](https://pypi.org/project/citationer/)

**Citationer** is a lightweight, local-first, zero-config CLI tool for researchers. Drop into a directory with bibliographic export files, run a single command, and get a complete literature analysis — from descriptive statistics to knowledge graphs and AI-powered topic labeling.

---

## Features

| Category | Capability |
|----------|-----------|
| 🔍 **Format Detection** | Auto-detect CNKI, Web of Science exports (.xlsx, .txt, .ciw) |
| 📊 **Descriptive Stats** | Yearly trends, top journals/authors/institutions, h-index, solo/coop rates |
| 🔗 **Network Analysis** | Keyword co-occurrence, author/institution collaboration, co-citation, bibliographic coupling |
| 📝 **Text Mining** | Tokenization (jieba + spaCy), keyword frequency, LDA/NMF topic modeling, TF-IDF summarization, clustering |
| 🤖 **LLM-Powered AI** | Topic labeling, literature review generation, trend identification, multi-dimensional classification — supports DeepSeek, OpenAI, Ollama |
| ⚙ **Configurable** | CLI-driven config (`config show/set/init`), env-var support, multi-provider LLM |
| 🎨 **Rich Terminal** | Color tables, progress bars, interactive HTML network graphs (Plotly) |
| 📦 **Pipe-friendly** | JSON/CSV/GEXF/GraphML export — works with `grep`, `jq`, Gephi, Cytoscape |

---

## Installation

```bash
# Recommended: isolated install via pipx
pipx install citationer

# Or via pip
pip install citationer

# With all optional dependencies (NLP, network, AI, viz)
pip install "citationer[all]"

# From source
git clone https://github.com/JasonCENG/citationer.git
cd citationer
pip install -e ".[all,dev]"
```

---

## Quick Start

```bash
# 1. Navigate to your literature directory
cd /path/to/literature

# 2. Scan for bibliographic files
citationer scan

# 3. Import into the local database
citationer import

# 4. Clean & deduplicate
citationer clean

# 5. View the overview dashboard
citationer stats overview
```

---

## Command Reference

### Data Management

```bash
citationer scan                  # Scan directory for bibliographic files
citationer status                # Quick status check
citationer import                # Import files into SQLite database
citationer clean                 # Validate & deduplicate records
```

### Descriptive Statistics (`stats`)

```bash
citationer stats overview        # Dashboard: totals, years, h-index, languages
citationer stats yearly          # Annual publication trend
citationer stats yearly --cumulative  # Cumulative trend
citationer stats journals --top 20    # Top journals
citationer stats authors --top 20     # Top authors (with Price's Law)
citationer stats institutions --top 20 # Top institutions
```

### Text Mining (`text`)

```bash
citationer text preprocess       # Tokenize + language detection
citationer text keywords --top 30     # Keyword frequency
citationer text keywords --per-year   # Keyword × year heatmap
citationer text topics --method lda   # LDA topic modeling
citationer text topics --method nmf   # NMF topic modeling
citationer text summarize              # TF-IDF extractive summary
citationer text cluster --method kmeans  # Document clustering
```

### Network Analysis (`network`)

```bash
citationer network keywords --top 50 --threshold 3   # Co-occurrence network
citationer network coauthors --min-papers 2           # Author collaboration
citationer network coauthors --type institutions       # Institution collaboration
citationer network cocitation --top 30                 # Co-citation analysis
citationer network coupling --top 30                   # Bibliographic coupling

# Export formats: csv, gexf, graphml, html (interactive)
citationer network keywords --output-format gexf --output graph.gexf
citationer network coauthors --viz --output network.html
```

### LLM-Powered Analysis (`ai`)

```bash
# Configure your LLM first
citationer config set llm.api_key sk-your-key
citationer config set llm.model deepseek-chat

citationer ai topics --auto-label     # Auto-label LDA topics
citationer ai summarize               # Generate literature review (200-500 words)
citationer ai trends                  # Identify research trends & gaps
citationer ai classify                # Multi-dimensional classification
citationer ai info                    # View LLM config & cache stats

# Preview without API call
citationer ai summarize --dry-run
```

### Configuration (`config`)

```bash
citationer config show                # View all settings
citationer config set llm.api_key sk-xxx  # Set API key
citationer config set llm.model gpt-4o    # Change model
citationer config set llm.base_url https://api.openai.com/v1  # Change provider
citationer config init                # Initialize config file with defaults
```

---

## LLM Provider Configuration

Citationer supports any OpenAI-compatible API. Edit `.citationer/config.yaml` or use env vars:

```yaml
# .citationer/config.yaml
llm:
  api_key: "sk-xxx"
  model: "deepseek-chat"
  base_url: "https://api.deepseek.com"
  temperature: 0.3
  max_tokens: 4096
```

| Provider | base_url |
|----------|----------|
| DeepSeek | `https://api.deepseek.com` |
| OpenAI | `https://api.openai.com/v1` |
| Ollama (local) | `http://localhost:11434/v1` |

Environment variables override the config file: `CITATIONER_LLM_API_KEY`, `CITATIONER_LLM_MODEL`, etc.

---

## Supported Bibliographic Formats

| Source | Format | Extensions | Status |
|--------|--------|-----------|--------|
| **Web of Science** | Plain text / Tab-delimited / Excel | `.txt`, `.ciw`, `.xlsx`, `.xls` | ✅ Stable |
| **CNKI (知网)** | Excel export | `.xlsx` | ✅ Stable |
| Scopus | CSV/Excel | `.csv`, `.xlsx` | 🔜 Phase 3 |
| PubMed | XML/MEDLINE | `.xml`, `.nbib` | 🔜 Phase 3 |
| BibTeX / RIS | Generic | `.bib`, `.ris` | 🔜 Phase 3 |

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[all,dev]"

# Run tests
pytest tests/ -v

# Lint & type check
ruff check src/ tests/
mypy src/ --ignore-missing-imports

# Coverage report
pytest tests/ --cov=src/citationer --cov-report=term-missing
```

---

## Documentation

- **[Handbook](docs/Handbook.md)** — Full user manual with examples
- **[PRD v2.0](docs/PRD-v2.0.md)** — Product requirements document
- **[PRD v1.0](docs/PRD-v1.0.md)** — Original PRD (historical)

---

## License

MIT © Jason Yu
