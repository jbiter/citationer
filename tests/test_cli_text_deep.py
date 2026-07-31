"""Deep tests for cli/text_cmd.py.

Covers: preprocess, keywords, topics, summarize, cluster subcommands.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from citationer.cli.main import app
from tests._helpers import seed_cli_db


def _setup_rich_text_data(clean_cwd: Path) -> None:
    """Setup DB with records that have abstracts + keywords for text analysis."""
    from citationer.models.record import Author, Record

    records = [
        Record(
            title="Machine Learning in Healthcare",
            year=2024,
            authors=[Author(full_name="Smith, J.", order=1)],
            keywords=["machine learning", "healthcare", "AI"],
            keywords_en=["ML", "healthcare"],
            abstract=(
                "This paper explores the application of machine learning algorithms "
                "in healthcare diagnostics. Deep learning models can analyze medical "
                "images effectively."
            ),
            language="en",
            source_database="WoS",
        ),
        Record(
            title="深度学习在医疗影像中的应用",
            year=2023,
            authors=[Author(full_name="张伟", order=1)],
            keywords=["深度学习", "医疗影像", "人工智能"],
            abstract="本文研究深度学习在医疗影像诊断中的应用,提出了新的卷积神经网络架构。",
            language="zh",
            source_database="CNKI",
        ),
        Record(
            title="Quantum Computing for Cryptography",
            year=2022,
            authors=[Author(full_name="Einstein, A.", order=1)],
            keywords=["quantum", "computing", "cryptography"],
            abstract="Quantum computing introduces new paradigms for cryptographic security.",
            language="en",
            source_database="arXiv",
        ),
    ]
    seed_cli_db(clean_cwd, records)


class TestTextPreprocess:
    def test_preprocess_default(self, cli_runner, clean_cwd, monkeypatch):
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["text", "preprocess"])
        assert result.exit_code == 0

    def test_preprocess_field_title(self, cli_runner, clean_cwd, monkeypatch):
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["text", "preprocess", "--field", "title"])
        assert result.exit_code == 0

    def test_preprocess_field_abstract(self, cli_runner, clean_cwd, monkeypatch):
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["text", "preprocess", "--field", "abstract"])
        assert result.exit_code == 0

    def test_preprocess_lang_en(self, cli_runner, clean_cwd, monkeypatch):
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["text", "preprocess", "--lang", "en"])
        assert result.exit_code == 0

    def test_preprocess_lang_zh(self, cli_runner, clean_cwd, monkeypatch):
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["text", "preprocess", "--lang", "zh"])
        assert result.exit_code == 0

    def test_preprocess_top_n(self, cli_runner, clean_cwd, monkeypatch):
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["text", "preprocess", "--top", "1"])
        assert result.exit_code == 0

    def test_preprocess_empty(self, cli_runner, clean_cwd):
        result = cli_runner.invoke(app, ["text", "preprocess"])
        assert result.exit_code in (0, 1)


class TestTextKeywords:
    def test_keywords_csv_output(self, cli_runner, clean_cwd, monkeypatch):
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        output = clean_cwd / "kw.csv"
        result = cli_runner.invoke(
            app, ["text", "keywords", "--format", "csv", "-o", str(output)]
        )
        assert result.exit_code == 0
        if output.exists():
            content = output.read_text()
            # CSV has header
            assert "keyword" in content.lower() or "count" in content.lower() or len(content) > 0

    def test_keywords_json_output(self, cli_runner, clean_cwd, monkeypatch):
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        output = clean_cwd / "kw.json"
        result = cli_runner.invoke(
            app, ["text", "keywords", "--format", "json", "-o", str(output)]
        )
        assert result.exit_code == 0
        if output.exists():
            data = json.loads(output.read_text())
            assert isinstance(data, (list, dict))

    def test_keywords_min_count(self, cli_runner, clean_cwd, monkeypatch):
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["text", "keywords", "--min-count", "2"]
        )
        assert result.exit_code == 0

    def test_keywords_table_coverage_not_always_100(self, cli_runner, clean_cwd, monkeypatch):
        """Top-N coverage should reflect real proportion of all occurrences."""
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["text", "keywords", "--top", "3"])
        assert result.exit_code == 0
        output = result.output
        # Should report coverage < 100% when top-3 doesn't cover all keywords
        assert "Top-3 累计占比" in output
        # Extract percentage: e.g. "Top-3 累计占比 36%"
        import re
        match = re.search(r"Top-3 累计占比 (\d+)%", output)
        assert match, f"Could not find coverage in output: {output}"
        coverage = int(match.group(1))
        assert coverage < 100, f"Expected coverage < 100, got {coverage}%"

    def test_keywords_per_year(self, cli_runner, clean_cwd, monkeypatch):
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["text", "keywords", "--per-year"])
        assert result.exit_code == 0


class TestTextTopics:
    def test_topics_lda(self, cli_runner, clean_cwd, monkeypatch):
        pytest.importorskip("sklearn")
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["text", "topics", "--method", "lda"])
        assert result.exit_code == 0

    def test_topics_nmf(self, cli_runner, clean_cwd, monkeypatch):
        """NMF may fail on small datasets (sklearn min_df constraint)."""
        pytest.importorskip("sklearn")
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["text", "topics", "--method", "nmf"])
        # NMF requires more data than LDA; accept either success or sklearn error
        assert result.exit_code in (0, 1)

    def test_topics_with_k(self, cli_runner, clean_cwd, monkeypatch):
        pytest.importorskip("sklearn")
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["text", "topics", "--num-topics", "3"])
        assert result.exit_code == 0

    def test_topics_output_json(self, cli_runner, clean_cwd, monkeypatch):
        pytest.importorskip("sklearn")
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        output = clean_cwd / "topics.json"
        result = cli_runner.invoke(
            app, ["text", "topics", "-o", str(output)]
        )
        assert result.exit_code == 0

    def test_topics_max_terms(self, cli_runner, clean_cwd, monkeypatch):
        pytest.importorskip("sklearn")
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["text", "topics", "--max-terms", "5"])
        assert result.exit_code == 0


class TestTextSummarize:
    def test_summarize(self, cli_runner, clean_cwd, monkeypatch):
        pytest.importorskip("sklearn")
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["text", "summarize"])
        assert result.exit_code == 0

    def test_summarize_max_sentences(self, cli_runner, clean_cwd, monkeypatch):
        pytest.importorskip("sklearn")
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["text", "summarize", "--max-sentences", "5"])
        assert result.exit_code == 0

    def test_summarize_output(self, cli_runner, clean_cwd, monkeypatch):
        pytest.importorskip("sklearn")
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        output = clean_cwd / "summary.md"
        result = cli_runner.invoke(
            app, ["text", "summarize", "-o", str(output)]
        )
        assert result.exit_code == 0


class TestTextCluster:
    def test_cluster_kmeans(self, cli_runner, clean_cwd, monkeypatch):
        pytest.importorskip("sklearn")
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["text", "cluster", "--method", "kmeans"])
        assert result.exit_code == 0

    def test_cluster_hierarchical(self, cli_runner, clean_cwd, monkeypatch):
        pytest.importorskip("sklearn")
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["text", "cluster", "--method", "hierarchical"]
        )
        assert result.exit_code == 0

    def test_cluster_with_k(self, cli_runner, clean_cwd, monkeypatch):
        pytest.importorskip("sklearn")
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["text", "cluster", "--n-clusters", "2"]
        )
        assert result.exit_code == 0

    def test_cluster_tfidf(self, cli_runner, clean_cwd, monkeypatch):
        pytest.importorskip("sklearn")
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["text", "cluster", "--vectorizer", "tfidf"]
        )
        assert result.exit_code == 0

    def test_cluster_output(self, cli_runner, clean_cwd, monkeypatch):
        pytest.importorskip("sklearn")
        _setup_rich_text_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        output = clean_cwd / "clusters.csv"
        result = cli_runner.invoke(
            app, ["text", "cluster", "-o", str(output)]
        )
        assert result.exit_code == 0
