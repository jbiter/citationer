# Installation

## From PyPI (recommended)

```bash
pip install --no-build-isolation citationer
```

The `--no-build-isolation` flag avoids a known hang in pip 26.x during editable install.

## With all optional features

```bash
pip install --no-build-isolation "citationer[all]"
```

This includes:
- `jieba` (Chinese tokenization)
- `gensim`, `scikit-learn` (topic modeling, clustering)
- `networkx`, `python-louvain`, `plotly` (network analysis)
- `openai` (LLM client)
- `wordcloud` (word clouds)
- `rapidfuzz` (fast string matching)

## From source

```bash
git clone https://github.com/jbiter/citationer.git
cd citationer
pip install --no-build-isolation -e ".[all,dev]"
```

## Standalone binary

Download a pre-built binary from [Releases](https://github.com/jbiter/citationer/releases):

```bash
./citationer --version
```

Build from source: `pyinstaller packaging/pyinstaller.spec`

## Verify

```bash
citationer --version
# citationer v5.0.1
```
