# Commands

Citationer exposes a single binary with subcommands. Run `citationer --help` for the full L1 overview, or `citationer <group> --help` for a specific group.

## Data management

```bash
citationer scan                  # Detect bibliographic files
citationer status                # Quick status check
citationer import                # Import files (clears old data)
citationer import --keep         # Append to existing data
citationer clean                 # Validate & deduplicate
citationer export csv -o out.csv # Export to CSV/JSON/BibTeX
```

## Descriptive statistics (`stats`)

```bash
citationer stats overview             # Dashboard
citationer stats yearly               # Braille line chart
citationer stats yearly --cumulative  # Dual bar+line chart
citationer stats yearly --table       # Data table
citationer stats journals --top 20    # Horizontal bar chart
citationer stats authors --top 20     # Bar chart + Price's Law
citationer stats institutions --top 20 # Bar chart
```

## Text mining (`text`)

```bash
citationer text preprocess       # Tokenize + language detection
citationer text keywords --top 30     # Keyword frequency
citationer text keywords --per-year   # Keyword × year heatmap
citationer text keywords --wordcloud   # Generate wordcloud PNG
citationer text topics --method lda   # LDA topic modeling
citationer text topics --method nmf   # NMF topic modeling
citationer text summarize            # TF-IDF extractive summary
citationer text cluster --method kmeans  # Document clustering
```

## Network analysis (`network`)

```bash
citationer network keywords --top 50 --threshold 3   # Co-occurrence network
citationer network coauthors --min-papers 2           # Author collaboration
citationer network coauthors --type institutions       # Institution collaboration
citationer network cocitation --top 30                 # Co-citation analysis
citationer network coupling --top 30                   # Bibliographic coupling
```

## Trend analysis (`trend`)

```bash
citationer trend hotspots --top 30        # Keyword burst detection
citationer trend strategy --top 50        # Strategic diagram
citationer trend river --top 8            # Thematic river
```

## Reports (`report`)

```bash
citationer report quick -o report.md       # Generate report
citationer report quick --enhance         # LLM-enhanced
citationer report custom config.yaml     # Custom YAML-configured
```

## Interactive mode (`interactive`)

```bash
citationer interactive                 # Guided step-by-step wizard
```

## Pipeline runner (`run`)

```bash
citationer run pipeline.yaml            # Execute declarative pipeline
```

## Web dashboard (`serve`)

启动本地 Web 仪表板。

```bash
citationer serve              # http://127.0.0.1:8000
citationer serve --port 8080  # 绑定到 8080 端口
citationer serve --reload     # 开发模式自动重载
```

需要 `[web]` extras：`pip install 'citationer[web]'`。

## Plugins (`plugins`)

列出已注册的解析器插件。

```bash
citationer plugins list       # 显示内置与第三方解析器来源
```

## Global options

```bash
--verbose, -v       # Detailed output
--quiet, -q         # Quiet mode
--output, -o PATH   # Output directory
--no-color          # Disable colored output
--version           # Show version
```
