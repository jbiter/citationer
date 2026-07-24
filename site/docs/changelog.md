# Changelog

All notable changes to Citationer are documented here. Versions follow
[Semantic Versioning](https://semver.org/).

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
