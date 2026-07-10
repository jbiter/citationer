# Quick Start

A minimal workflow takes 4 commands:

```bash
cd /path/to/your/literature

# 1. Scan for bibliographic files
citationer scan

# 2. Import into the local database
citationer import

# 3. Clean & deduplicate
citationer clean

# 4. View the overview dashboard
citationer stats overview
```

## Interactive wizard

If you prefer a guided step-by-step flow, use:

```bash
citationer interactive
```

## Declarative pipeline

For reproducible batch analysis, define a YAML pipeline:

```bash
# examples/standard_pipeline.yaml
name: standard_analysis
output_dir: output/standard
steps:
  - name: overview
    action: stats
    type: overview
  - name: top_journals
    action: stats
    type: journals
    top: 20
  - name: topics
    action: text
    type: topics
    num_topics: 5
```

Run it:

```bash
citationer run examples/standard_pipeline.yaml
```

## Output structure

Generated files go to `./output/`:

```
output/
├── cls/                  # CSV / JSON / BibTeX exports
│   └── cleaned_records.csv
└── viz/                  # Charts and visualisations
    └── yearly_trend.png
```
