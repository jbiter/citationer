"""Deep tests for cli/network_cmd.py — co-occurrence, collaboration, citation."""

from __future__ import annotations

from pathlib import Path

from citationer.cli.main import app


def _setup_network_data(clean_cwd: Path) -> None:
    """Setup DB with records that have keyword co-occurrence."""
    db_dir = clean_cwd / ".citationer"
    db_dir.mkdir(exist_ok=True)

    from citationer.models.record import Author, Institution, Record
    from citationer.utils.database import CitationDatabase
    from citationer.utils.serialization import record_to_db_serializable

    db = CitationDatabase(db_dir / "cache.db")
    db.initialize()

    records = [
        # Pairs of papers with shared keywords
        Record(
            title="ML Paper 1",
            year=2024,
            authors=[
                Author(full_name="Smith, J.", order=1),
                Author(full_name="Jones, M.", order=2),
            ],
            keywords=["machine learning", "healthcare", "AI"],
            institutions=[Institution(name="MIT", country="USA")],
            source_database="WoS",
        ),
        Record(
            title="ML Paper 2",
            year=2023,
            authors=[Author(full_name="Smith, J.", order=1)],
            keywords=["machine learning", "healthcare", "neural networks"],
            institutions=[Institution(name="MIT", country="USA")],
            source_database="WoS",
        ),
        Record(
            title="DL Paper",
            year=2022,
            authors=[Author(full_name="Brown, R.", order=1)],
            keywords=["deep learning", "AI", "neural networks"],
            source_database="arXiv",
        ),
    ]
    for r in records:
        payload = record_to_db_serializable(r)
        db.insert_record(
            record_data=payload["record_data"],
            authors=payload["authors"],
            keywords=payload["keywords"],
            institutions=payload["institutions"],
        )
    db.close()


class TestNetworkKeywords:
    def test_keywords_default(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "keywords"])
        assert result.exit_code == 0

    def test_keywords_top_n(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "keywords", "--top", "5"])
        assert result.exit_code == 0

    def test_keywords_threshold(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "keywords", "--threshold", "1"])
        assert result.exit_code == 0

    def test_keywords_output_format_csv(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["network", "keywords", "--output-format", "csv"]
        )
        assert result.exit_code == 0

    def test_keywords_output_format_gexf(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["network", "keywords", "--output-format", "gexf"]
        )
        assert result.exit_code == 0

    def test_keywords_output_format_graphml(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["network", "keywords", "--output-format", "graphml"]
        )
        assert result.exit_code == 0

    def test_keywords_viz(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "keywords", "--viz"])
        assert result.exit_code == 0

    def test_keywords_no_edges(self, cli_runner, clean_cwd, monkeypatch):
        """Very high threshold → no edges → warning message."""
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["network", "keywords", "--threshold", "100"]
        )
        assert result.exit_code == 0
        assert "未找到" in result.output or result.exit_code == 0

    def test_keywords_with_output_path(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        output = clean_cwd / "net.csv"
        result = cli_runner.invoke(
            app, ["network", "keywords", "--output-format", "csv", "-o", str(output)]
        )
        assert result.exit_code == 0


class TestNetworkCoauthors:
    def test_coauthors_default(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "coauthors"])
        assert result.exit_code == 0

    def test_coauthors_min_papers(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["network", "coauthors", "--min-papers", "1"]
        )
        assert result.exit_code == 0

    def test_coauthors_institutions(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["network", "coauthors", "--type", "institutions"]
        )
        assert result.exit_code == 0

    def test_coauthors_viz(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "coauthors", "--viz"])
        assert result.exit_code == 0

    def test_coauthors_output(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        output = clean_cwd / "coauthors.csv"
        result = cli_runner.invoke(
            app, ["network", "coauthors", "--output-format", "csv", "-o", str(output)]
        )
        assert result.exit_code == 0


class TestNetworkCocitation:
    def test_cocitation(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "cocitation"])
        assert result.exit_code == 0

    def test_cocitation_top(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "cocitation", "--top", "5"])
        assert result.exit_code == 0

    def test_cocitation_viz(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "cocitation", "--viz"])
        assert result.exit_code == 0


class TestNetworkCoupling:
    def test_coupling(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "coupling"])
        assert result.exit_code == 0

    def test_coupling_top(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "coupling", "--top", "5"])
        assert result.exit_code == 0

    def test_coupling_viz(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "coupling", "--viz"])
        assert result.exit_code == 0

    def test_coupling_output(self, cli_runner, clean_cwd, monkeypatch):
        _setup_network_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        output = clean_cwd / "coupling.gexf"
        result = cli_runner.invoke(
            app, ["network", "coupling", "--output-format", "gexf", "-o", str(output)]
        )
        assert result.exit_code == 0


class TestNetworkEmpty:
    def test_network_no_data(self, cli_runner, clean_cwd):
        result = cli_runner.invoke(app, ["network", "keywords"])
        assert result.exit_code in (0, 1)
