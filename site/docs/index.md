# Citationer v4

> **A terminal-first bibliometric analysis CLI tool** — scan, import, analyze, and visualize your literature collection.

**Citationer** is a lightweight, local-first, zero-config CLI tool for researchers. Drop into a directory with bibliographic export files, run a single command, and get a complete literature analysis — from descriptive statistics with terminal charts to knowledge graphs and AI-powered topic labeling.

## Features

| Category | Capability |
|----------|-----------|
| 🔍 **Format Detection** | Auto-detect CNKI, WoS, Scopus, PubMed, CSSCI, BibTeX, RIS |
| 📊 **Descriptive Stats** | Yearly trends, top journals/authors/institutions, h-index |
| 📈 **Terminal Charts** | Braille line charts + Unicode bar charts in terminal |
| 🔗 **Network Analysis** | Keyword co-occurrence, author/institution collaboration, co-citation, bibliographic coupling |
| 📝 **Text Mining** | Tokenization (jieba), keyword frequency, LDA/NMF topic modeling, TF-IDF summarization, clustering |
| 🤖 **LLM-Powered AI** | Topic labeling, literature review, trend identification, multi-dim classification (DeepSeek/OpenAI/Ollama) |
| 📈 **Trend Analysis** | Burst detection, strategic diagram, thematic river |
| 📄 **Reports** | Markdown/HTML report generation, LLM-enhanced |
| ⚙ **Configurable** | CLI-driven config, multi-provider LLM, env-var support |
| 🆕 **Interactive** | Step-by-step wizard mode |
| 🆕 **Pipeline** | Declarative YAML pipeline runner |

## Quick Start

```bash
pip install --no-build-isolation citationer
cd /path/to/your/literature
citationer scan
citationer import
citationer clean
citationer stats overview
```

## GitHub

[jbiter/citationer](https://github.com/jbiter/citationer)
