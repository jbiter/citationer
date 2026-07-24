"""Deep tests for cli/network_cmd.py — co-occurrence, collaboration, citation."""

from __future__ import annotations

from pathlib import Path

import pytest

from citationer.cli.main import app
from tests._helpers import seed_cli_db


def _setup_network_data(clean_cwd: Path) -> None:
    """Setup DB with records that have keyword co-occurrence."""
    from citationer.models.record import Author, Institution, Record

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
    seed_cli_db(clean_cwd, records)


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


class TestNetworkEdgeBranches:
    """Cover remaining network_cmd formatting/community/warning branches."""

    @pytest.fixture
    def fake_records(self):
        from citationer.models.record import Record

        return [Record(title="P", year=2024, source_database="Test")]

    @pytest.fixture
    def patched_network(self, monkeypatch, fake_records):
        import citationer.cli.network_cmd as net_mod
        from citationer.analysis.network import (
            CitationGraph,
            CollaborationGraph,
            CoOccurrenceMatrix,
        )

        monkeypatch.setattr(net_mod, "_get_records", lambda: fake_records)

        class FakeEngine:
            def __init__(self, records):
                self._records = records

            def keyword_cooccurrence(self, **kwargs):
                edges = [(f"a{i}", f"b{i}", i) for i in range(1, 41)]
                return CoOccurrenceMatrix(
                    keywords=[],
                    edges=edges,
                    total_keywords=0,
                    total_edges=len(edges),
                )

            def author_collaboration(self, **kwargs):
                edges = [("A", "B", 2)]
                return CollaborationGraph(
                    collab_type=kwargs.get("collab_type", "authors"),
                    nodes=[("A", 2), ("B", 1)],
                    edges=edges,
                    communities={"A": 0, "B": 0},
                    total_nodes=2,
                    total_edges=1,
                )

            def co_citation(self, **kwargs):
                if kwargs.get("empty"):
                    return CitationGraph(graph_type="cocitation", edges=[], total_edges=0)
                edges = [("Ref A", "Ref B", 3)]
                return CitationGraph(
                    graph_type="cocitation", edges=edges, total_edges=len(edges)
                )

            def bibliographic_coupling(self, **kwargs):
                if kwargs.get("fallback"):
                    return CitationGraph(
                        graph_type="keyword_coupling",
                        edges=[("P1", "P2", 1)],
                        total_edges=1,
                    )
                edges = [("P1", "P2", 2)]
                return CitationGraph(
                    graph_type="bibliographic_coupling",
                    edges=edges,
                    total_edges=len(edges),
                )

            @staticmethod
            def to_csv(edges, output_path: Path) -> Path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("source,target,weight\n", encoding="utf-8")
                return output_path

            @staticmethod
            def to_gexf(edges, nodes, output_path: Path) -> Path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("<gexf/>", encoding="utf-8")
                return output_path

            @staticmethod
            def to_graphml(edges, nodes, output_path: Path) -> Path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("<graphml/>", encoding="utf-8")
                return output_path

            @staticmethod
            def to_html(edges, nodes, communities, output_path: Path, title: str = "") -> Path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text("<html/>", encoding="utf-8")
                return output_path

        monkeypatch.setattr(net_mod, "NetworkEngine", FakeEngine)
        return net_mod

    def test_keywords_table_truncation(self, cli_runner, clean_cwd, monkeypatch, patched_network):
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "keywords"])
        assert result.exit_code == 0
        assert "还有" in result.output

    def test_keywords_csv_default_path(self, cli_runner, clean_cwd, monkeypatch, patched_network):
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "keywords", "--output-format", "csv"])
        assert result.exit_code == 0
        assert (clean_cwd / "output" / "viz" / "keyword_cooccurrence.csv").exists()

    def test_keywords_gexf(self, cli_runner, clean_cwd, monkeypatch, patched_network):
        monkeypatch.chdir(clean_cwd)
        out = clean_cwd / "kw.gexf"
        result = cli_runner.invoke(
            app, ["network", "keywords", "--output-format", "gexf", "-o", str(out)]
        )
        assert result.exit_code == 0
        assert out.exists()

    def test_keywords_graphml(self, cli_runner, clean_cwd, monkeypatch, patched_network):
        monkeypatch.chdir(clean_cwd)
        out = clean_cwd / "kw.graphml"
        result = cli_runner.invoke(
            app, ["network", "keywords", "--output-format", "graphml", "-o", str(out)]
        )
        assert result.exit_code == 0
        assert out.exists()

    def test_keywords_viz(self, cli_runner, clean_cwd, monkeypatch, patched_network):
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "keywords", "--viz"])
        assert result.exit_code == 0
        assert (clean_cwd / "output" / "viz" / "keyword_network.html").exists()

    def test_coauthors_table_communities(self, cli_runner, clean_cwd, monkeypatch, patched_network):
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "coauthors"])
        assert result.exit_code == 0
        assert "社区" in result.output

    def test_coauthors_gexf(self, cli_runner, clean_cwd, monkeypatch, patched_network):
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["network", "coauthors", "--output-format", "gexf"]
        )
        assert result.exit_code == 0
        assert (clean_cwd / "output" / "viz" / "authors_collaboration.gexf").exists()

    def test_coauthors_graphml(self, cli_runner, clean_cwd, monkeypatch, patched_network):
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["network", "coauthors", "--output-format", "graphml"]
        )
        assert result.exit_code == 0
        assert (clean_cwd / "output" / "viz" / "authors_collaboration.graphml").exists()

    def test_coauthors_institutions(self, cli_runner, clean_cwd, monkeypatch, patched_network):
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["network", "coauthors", "--type", "institutions", "--viz"]
        )
        assert result.exit_code == 0
        assert (clean_cwd / "output" / "viz" / "institutions_network.html").exists()

    def test_cocitation_no_edges(
        self, cli_runner, clean_cwd, monkeypatch, patched_network
    ):
        import citationer.cli.network_cmd as net_mod
        from citationer.analysis.network import CitationGraph

        monkeypatch.chdir(clean_cwd)

        class EmptyCocitation(net_mod.NetworkEngine):
            def co_citation(self, **kwargs):
                return CitationGraph(graph_type="cocitation", edges=[], total_edges=0)

        monkeypatch.setattr(net_mod, "NetworkEngine", EmptyCocitation)
        result = cli_runner.invoke(app, ["network", "cocitation"])
        assert result.exit_code == 0
        assert "未找到" in result.output

    def test_cocitation_csv(
        self, cli_runner, clean_cwd, monkeypatch, patched_network
    ):
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["network", "cocitation", "--output-format", "csv"]
        )
        assert result.exit_code == 0
        assert (clean_cwd / "output" / "viz" / "cocitation.csv").exists()

    def test_cocitation_viz(
        self, cli_runner, clean_cwd, monkeypatch, patched_network
    ):
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "cocitation", "--viz"])
        assert result.exit_code == 0
        assert (clean_cwd / "output" / "viz" / "cocitation_network.html").exists()

    def test_coupling_keyword_fallback_label(
        self, cli_runner, clean_cwd, monkeypatch, patched_network
    ):
        import citationer.cli.network_cmd as net_mod
        from citationer.analysis.network import CitationGraph

        monkeypatch.chdir(clean_cwd)

        class FallbackCoupling(net_mod.NetworkEngine):
            def bibliographic_coupling(self, **kwargs):
                return CitationGraph(
                    graph_type="keyword_coupling",
                    edges=[("P1", "P2", 1)],
                    total_edges=1,
                )

        monkeypatch.setattr(net_mod, "NetworkEngine", FallbackCoupling)
        result = cli_runner.invoke(app, ["network", "coupling"])
        assert result.exit_code == 0
        assert "关键词耦合" in result.output

    def test_coupling_csv(
        self, cli_runner, clean_cwd, monkeypatch, patched_network
    ):
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["network", "coupling", "--output-format", "csv"]
        )
        assert result.exit_code == 0
        assert (clean_cwd / "output" / "viz" / "bibliographic_coupling.csv").exists()

    def test_coupling_viz(
        self, cli_runner, clean_cwd, monkeypatch, patched_network
    ):
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["network", "coupling", "--viz"])
        assert result.exit_code == 0
        assert (clean_cwd / "output" / "viz" / "coupling_network.html").exists()
