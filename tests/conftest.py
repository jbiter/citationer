"""Shared pytest fixtures for the citationer test suite.

These fixtures provide:
- Temporary SQLite databases pre-initialized
- Sample Record objects covering various field completeness
- Isolated working directories (clean_cwd) to avoid polluting user `.citationer/`
- Stub LLM client for AI command tests
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from citationer.models.record import Author, Institution, Record
from citationer.utils.database import CitationDatabase

# `make_record` lives in tests/_factories.py.  Re-exported here so
# existing call-sites that imported it from conftest continue to work.
from tests._factories import make_record  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_records() -> list[Record]:
    """10 records covering various field completeness levels.

    Designed to exercise:
    - Records with and without DOI
    - Chinese vs English language
    - Solo vs multi-author
    - Records with funding, references, institutions
    - Multiple years (for grouping/statistics)
    """
    return [
        make_record(
            title="Machine Learning in Healthcare",
            year=2024,
            doi="10.1000/ml-health-2024",
            authors=[
                Author(full_name="Smith, John", order=1),
                Author(full_name="Jones, Mary", order=2),
            ],
            keywords=["machine learning", "healthcare"],
            keywords_en=["ML", "health"],
            abstract="A study on ML in healthcare.",
            citation_count=15,
            source_database="WoS",
            source_file="wos_2024.txt",
        ),
        make_record(
            title="深度学习在医疗影像中的应用",
            year=2023,
            doi="10.1000/dl-medical-2023",
            authors=[Author(full_name="张伟", order=1)],
            keywords=["深度学习", "医疗影像"],
            language="zh",
            source_database="CNKI",
            source_file="cnki_2023.xlsx",
        ),
        make_record(
            title="Quantum Computing for Cryptography",
            year=2024,
            authors=[Author(full_name="Einstein, Albert", order=1)],
            keywords=["quantum computing", "cryptography"],
            citation_count=42,
            source_database="arXiv",
            source_file="arxiv.txt",
        ),
        make_record(
            title="A Survey of Neural Networks",
            year=2022,
            doi="10.1000/nn-survey",
            authors=[
                Author(full_name="Author A", order=1),
                Author(full_name="Author B", order=2),
                Author(full_name="Author C", order=3),
            ],
            keywords=["neural networks", "deep learning"],
            abstract="Comprehensive survey.",
            funding=["National Science Foundation"],
            citation_count=100,
            source_database="WoS",
        ),
        make_record(
            title="Bibliometric Analysis Methods",
            year=2023,
            authors=[Author(full_name="Garfield, E.", order=1)],
            keywords=["bibliometrics", "citation analysis"],
            citation_count=8,
            source_database="Scopus",
        ),
        # Duplicate (same DOI as record 0) — should be merged by dedup
        make_record(
            title="ML in Healthcare (variant)",
            year=2024,
            doi="10.1000/ml-health-2024",
            authors=[Author(full_name="Smith, J.", order=1)],
            abstract="Different abstract text.",
            source_database="Scopus",
        ),
        make_record(
            title="Solar Cell Efficiency Improvements",
            year=2022,
            authors=[Author(full_name="Curie, Marie", order=1)],
            keywords=["solar cells", "renewable energy"],
            institutions=[Institution(name="CNRS", country="France")],
            references=["Reference 1", "Reference 2"],
            citation_count=20,
            source_database="WoS",
        ),
        # Edge: no year, no DOI, no abstract (year/citation_count fall back
        # to 0 so db_loader doesn't hit BUG-001 with empty-string int fields;
        # real Pydantic fields stay None at the model level via conversion)
        make_record(
            title="Orphan Paper",
            year=None,
            doi=None,
            journal=None,
            abstract=None,
            citation_count=0,
            keywords=[],
            source_database="TestDB",
        ),
        # Edge: very long title
        make_record(
            title="A" * 500,
            year=2024,
            keywords=["edge", "test"],
            source_database="TestDB",
        ),
        # Edge: many authors (10)
        make_record(
            title="Big Collaboration Study",
            year=2024,
            authors=[Author(full_name=f"Author {i}", order=i + 1) for i in range(10)],
            keywords=["collaboration", "big science"],
            source_database="WoS",
        ),
    ]


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_db(tmp_path: Path) -> Iterator[CitationDatabase]:
    """A pre-initialized temporary SQLite database.

    Yields a CitationDatabase pointing at tmp_path/cache.db, with all
    tables and indexes created.  Use this instead of manually
    initializing in each test.
    """
    db = CitationDatabase(tmp_path / "cache.db")
    db.initialize()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def tmp_db_path(tmp_path: Path) -> Path:
    """Path to a pre-initialized temporary database (no open connection)."""
    db = CitationDatabase(tmp_path / "cache.db")
    db.initialize()
    db.close()
    return tmp_path / "cache.db"


# ---------------------------------------------------------------------------
# Filesystem isolation
# ---------------------------------------------------------------------------


@pytest.fixture
def clean_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Change into a clean tmp_path during the test.

    Prevents tests from creating `.citationer/` or `citationer_output/`
    in the user's actual working directory.  The original cwd is
    restored on teardown.
    """
    monkeypatch.chdir(tmp_path)
    yield tmp_path


@pytest.fixture
def disable_color(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force-disable ANSI colors for stable output assertions."""
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("CITATIONER_NO_COLOR", "1")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@pytest.fixture
def cli_runner() -> CliRunner:
    """Typer CliRunner for end-to-end CLI command tests.

    Triggers lazy registration of all subcommands by invoking
    _register() directly — CliRunner does not go through __call__,
    so the _LazyTyper hook would not fire.
    """
    from citationer.cli.main import _register

    _register()
    return CliRunner()


# ---------------------------------------------------------------------------
# LLM mocking
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm_response(monkeypatch: pytest.MonkeyPatch):
    """Replace LLMClient.query with a stub returning a canned response.

    Returns a callable that lets each test customize the stub's output:
        resp = mock_llm_response(content="...", tokens=42)
    """
    from citationer.llm import client as llm_client_mod

    def _install(content: str = "stub LLM response", tokens: int = 10) -> None:
        from citationer.llm.client import LLMResponse

        def _stub_query(
            prompt: str,
            records: list | None = None,
            *,
            dry_run: bool = False,
            **kwargs,
        ) -> LLMResponse:
            if dry_run:
                return LLMResponse(
                    content="[DRY RUN] " + prompt[:200],
                    model="stub",
                    tokens_used=0,
                    cached=False,
                )
            return LLMResponse(
                content=content,
                model="stub-model",
                tokens_used=tokens,
                cached=False,
            )

        monkeypatch.setattr(llm_client_mod.LLMClient, "query", _stub_query)

    return _install


@pytest.fixture
def stub_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide a fake API key so LLMClient construction succeeds."""
    monkeypatch.setenv("CITATIONER_LLM_API_KEY", "sk-test-fake-key-for-tests")
    monkeypatch.setenv("CITATIONER_LLM_BASE_URL", "http://localhost:9999/v1")
    monkeypatch.setenv("CITATIONER_LLM_MODEL", "stub-model")


# ---------------------------------------------------------------------------
# Environment hygiene
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip any citationer env vars that might leak from the host shell.

    Runs automatically before every test to prevent contamination from
    user shell environment.
    """
    for var in (
        "CITATIONER_LLM_API_KEY",
        "CITATIONER_LLM_MODEL",
        "CITATIONER_LLM_BASE_URL",
        "CITATIONER_LLM_TEMPERATURE",
        "CITATIONER_LLM_MAX_TOKENS",
        "DEEPSEEK_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)
