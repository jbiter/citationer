# Changelog

All notable changes to Citationer are documented here. Versions follow
[Semantic Versioning](https://semver.org/).

## v5.0.0 — 2026-07-25

- **P5-1 Multi-Dataset Comparison Analysis**: new `citationer compare` command
  group (overview / trends / topics / network) for comparing multiple imported
  datasets in-memory, without database schema changes.
  - Group records by `source_database` (splitting composite values on `+`) or
    by `source_file`.
  - Pairwise DOI overlap, fuzzy title overlap, keyword Jaccard, and shared
    authors / institutions.
  - Output as Rich table, JSON, or CSV.
- Major version bump signals the start of Phase 5 feature work.

## v4.10.0 — 2026-07-25

- Completed the final CLI coverage push: `ai_cmd`, `stats_cmd`, `trend_cmd`,
  `config_cmd`, and `import_cmd` all raised above 85%.
- Added deep tests for missing-key / dry-run / mocked LLM paths, empty-data
  branches, `--table` / `--save` defaults, parser error handling, JSON import
  summary, and trend no-data / ImportError / icon branches.
- Project-wide test coverage reached ~93%.

## v4.9.0 — 2026-07-25

- Resolved the remaining Phase 4 technical debt by raising test coverage across
  `interactive_cmd`, `terminal_charts`, `network_cmd`, `llm/client`, `scopus`,
  and `cssci`.
- Fixed minor parser issues: Scopus "Book Chapter" doc-type ordering and CSSCI
  column matching now prefer the longest matching header.
- Corrected the interactive wizard database-empty check and added CSSCI
  `journal_en` output.

## v4.8.0 — 2026-07-24

- Dedup Layer 3 now prompts for human confirmation in interactive `citationer clean`;
  use `--non-interactive` to keep the legacy auto-merge behavior.
- Unified shared test fixtures (`tests._helpers.seed_cli_db`, `tests._factories.make_record`)
  and expanded WoS parser test coverage to 96%.
- Refreshed PRD documentation to reflect the v4.7.0+ state.

## v4.7.0 — 2026-07-23

`citationer query` DSL filter on imported records (P5-10). Trusted Publishing
(OIDC) enabled for PyPI releases.

## v4.6.6 — 2026-07-23

Review cleanups: deduplicate test `_r()` factories and extract dedup `_bucket_by`
helper.

## v4.6.5 — 2026-07-22

Batch of 7 bug fixes (BUG-008 through BUG-014).

## v4.6.4 — 2026-07-17

Review fixes.

## v4.6.3 — 2026-07-17

Version bump (`pyproject.toml` alignment).

## v4.6.2 — 2026-07-16

CI lint fixes in test suite.

## v4.6.1 — 2026-07-16

Fix dedup handling of records with `year=None`.

## v4.6.0 — 2026-07-10

Interactive wizard: save current analysis as a real report file.

## v4.5.0 — 2026-07-10

Report template system: `simple` template for concise summaries.

## v4.4.0 — 2026-07-10

Funding analysis: `citationer stats funding`.

## v4.3.0 — 2026-07-10

Standalone binary build via PyInstaller (Linux/macOS/Windows).

## v4.2.0 — 2026-07-10

MkDocs documentation site with GitHub Pages deployment.

## v4.1.2 — 2026-07-10

Bug fixes only. No new features.

## v4.1.1 — 2026-07-10

Critical bug fix for `db_loader`.

## v4.1.0 — 2026-07-09

Major test coverage milestone: 35% → 80%. 559 tests added across
17 new test files. End-to-end CLI testing infrastructure added.

## v4.0.x — 2026-07

Parser expansion phase. Added Scopus, PubMed, CSSCI, BibTeX, RIS
parsers. Interactive wizard and declarative YAML pipeline runner.

## v3.0.x — 2026-07

Trend analysis and report generation. Burst detection, strategic
diagram, thematic river. Markdown/HTML reports with optional LLM
enhancement.

## v2.x — 2026-07

Text mining, LLM integration, and network analysis. Chinese/English
NLP via jieba + spaCy. Multi-provider LLM support.

## v1.x — 2026-07

Initial release. CNKI + WoS parsers, basic descriptive statistics,
SQLite cache, CI/CD, PyPI publication.
