# Changelog

All notable changes to Citationer are documented here. Versions follow
[Semantic Versioning](https://semver.org/).

## v5.1.3 — 2026-08-10

### LLM / 查询 / 模型 / 网络导出健壮性

- 修复 LLM API 异常未捕获导致 CLI 崩溃的问题，现在返回友好的错误信息。
- 修复旧数据库缺少 `llm_cache` 表时 AI 调用报错的问题，查询缓存前自动初始化表结构。
- 修复 `citationer ai topics --no-auto-label` 仍要求配置 API Key 的问题。
- 修复 `citationer query` 中 `None` 值被当作小于任何数的比较错误。
- 修复 `Author.__hash__` 与 `__eq__` 不一致的问题（现在仅按姓名小写哈希）。
- 修复网络图 `gexf` / `graphml` 导出不会自动创建父目录的问题。

### Web UI 安全与资源泄漏

- 修复图表端点 `/api/charts/*` 产生的临时文件泄漏问题，响应后通过 `BackgroundTask` 清理。
- 修复 `get_db()` 依赖未关闭数据库连接的问题，改用 `yield` 上下文管理器。
- 为 `POST /api/data/scan|import|clean` 增加 `X-Requested-With` 请求头校验，防止 CSRF。
- 收紧 CORS，仅允许 `localhost` / `127.0.0.1` 来源。
- 添加 `X-Frame-Options: DENY` 响应头，防止点击劫持。
- 修复 `citationer serve --reload` 不生效的问题。

### CLI 全局选项与帮助信息

- 全局选项 `--config` / `--output` 现在会通过环境变量传递给子命令，并在命令结束后清理，避免污染后续调用。
- L1 帮助概览补充了 `query`、`interactive`、`run`、`stats funding`、`export ris/xlsx` 等缺失的命令。
- 将用户提示语中的旧可执行名 `ctr` 统一替换为 `citationer`。

## v5.1.2 — 2026-07-31

- 修复 BibTeX 解析器无法处理嵌套大括号的问题（如 `{Role of {BRCA1} in DNA repair}`）。
- 修复 PubMed XML 年份提取优先使用 `DateCompleted`/`DateRevised` 而非实际发表日期的问题。
- 修复 WoS `C1` 地址连续行使用 `; ` 连接导致机构解析丢失的问题。
- 修复 CSSCI 文本文件硬编码 UTF-8、无法读取 GBK 编码导出的问题。
- 修复 Scopus CSV/Excel 未读取 `Affiliations` 列导致机构缺失的问题。
- 修复 WoS `.xls` 解析未调用 `xlrd` 资源释放的问题。

## v5.1.1 — 2026-07-31

- 修复 `avg_citations` 排除零引用记录的问题，现在计入所有 `citation_count` 非空记录。
- 修复 `first_author_dist` 使用 `authors[0]` 而非 `order` 元数据的问题。
- 修复 `citationer text keywords` 的 Top-N 累计占比恒为 100% 的问题。
- 修复 `citationer import` 在空目录运行时先清空数据库的缺陷，并统一自动检测扩展名。
- 修复 `citationer interactive` 中整数输入未校验导致崩溃的问题。
- 为 `import` / `text` / `query` / `compare` / `network` 的 `--format` 选项增加非法值校验。

## v5.1.0 — 2026-08

- **P5-2 Web UI**：新增 `citationer serve` 命令，启动基于 FastAPI
  的本地仪表板，提供 stats、network、compare 的 JSON 接口与交互式图表。

## v5.0.2 — 2026-07-25

- Updated user handbook and documentation site titles from v4 to v5 to match
  the current software version.
- Fixed `SECURITY.md` supported-versions table: 5.0.x is now supported and
  4.0.x is not.
- Fixed stale version assertion in `tests/test_cli.py` to check the actual
  current version instead of a hardcoded "4.0" string.

## v5.0.1 — 2026-07-25

- Added PRD v4.0 with rescheduled Phase 5 (v5.x) and Phase 6 (v6.x) roadmaps.
- Dropped P5-6 (conda-forge) and P5-9 (Docker) from the roadmap.
- Raised `compare_cmd.py` test coverage from 78% to 100%; project coverage now
  93.13%.

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
