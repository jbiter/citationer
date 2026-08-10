"""Tests for the NetworkEngine module."""


from citationer.analysis.network import NetworkEngine
from citationer.models.record import Author, Institution
from tests._factories import make_record


class TestKeywordCooccurrence:
    def test_basic_cooccurrence(self):
        records = [
            make_record(keywords=["machine learning", "deep learning", "AI"]),
            make_record(keywords=["machine learning", "neural networks"]),
            make_record(keywords=["deep learning", "neural networks"]),
        ]
        engine = NetworkEngine(records)
        result = engine.keyword_cooccurrence(top_n=10, threshold=1)

        assert result.total_edges > 0
        # "machine learning" and "deep learning" co-occur in record 1
        edge_keywords = {(a, b) for a, b, _ in result.edges}
        assert ("deep learning", "machine learning") in edge_keywords or \
               ("machine learning", "deep learning") in edge_keywords

    def test_threshold_filter(self):
        records = [
            make_record(keywords=["AI", "ML"]),
            make_record(keywords=["AI", "DL"]),
            make_record(keywords=["ML", "DL"]),
        ]
        engine = NetworkEngine(records)
        result_high = engine.keyword_cooccurrence(top_n=10, threshold=3)
        result_low = engine.keyword_cooccurrence(top_n=10, threshold=1)

        # High threshold should have fewer edges
        assert len(result_high.edges) <= len(result_low.edges)

    def test_empty_records(self):
        engine = NetworkEngine([])
        result = engine.keyword_cooccurrence()
        assert result.total_edges == 0
        assert result.total_keywords == 0

    def test_top_n_filter(self):
        records = [
            make_record(keywords=[f"kw{i}"]) for i in range(20)
        ]
        # Add a pair that co-occurs
        records.append(make_record(keywords=["kw0", "kw1"]))
        engine = NetworkEngine(records)
        result = engine.keyword_cooccurrence(top_n=5, threshold=1)
        assert result.total_keywords <= 5


class TestAuthorCollaboration:
    def test_basic_collaboration(self):
        records = [
            make_record(
                title="Paper 1",
                authors=[
                    Author(full_name="Smith, John", order=1),
                    Author(full_name="Jones, Mary", order=2),
                ],
            ),
            make_record(
                title="Paper 2",
                authors=[
                    Author(full_name="Smith, John", order=1),
                    Author(full_name="Brown, Tom", order=2),
                ],
            ),
        ]
        engine = NetworkEngine(records)
        result = engine.author_collaboration(min_papers=1)

        assert result.collab_type == "authors"
        assert result.total_nodes == 3  # Smith, Jones, Brown
        # Smith-Jones and Smith-Brown
        assert result.total_edges == 2

    def test_min_papers_filter(self):
        records = [
            make_record(authors=[
                Author(full_name="Smith, John", order=1),
                Author(full_name="Jones, Mary", order=2),
            ]),
            make_record(authors=[
                Author(full_name="Smith, John", order=1),
            ]),
        ]
        engine = NetworkEngine(records)
        result = engine.author_collaboration(min_papers=2)
        # Only Smith has >= 2 papers
        assert result.total_nodes == 1
        assert result.total_edges == 0  # Jones filtered out

    def test_single_author_papers(self):
        records = [
            make_record(authors=[Author(full_name="Smith, John", order=1)]),
            make_record(authors=[Author(full_name="Jones, Mary", order=1)]),
        ]
        engine = NetworkEngine(records)
        result = engine.author_collaboration(min_papers=1)
        # No edges — each paper has only 1 author
        assert result.total_edges == 0

    def test_institution_collaboration(self):
        records = [
            make_record(
                institutions=[
                    Institution(name="Harvard University"),
                    Institution(name="MIT"),
                ],
            ),
            make_record(
                institutions=[
                    Institution(name="Harvard University"),
                    Institution(name="Stanford University"),
                ],
            ),
        ]
        engine = NetworkEngine(records)
        result = engine.author_collaboration(
            min_papers=1, collab_type="institutions"
        )
        assert result.collab_type == "institutions"
        assert result.total_nodes == 3


class TestCoCitation:
    def test_basic_cocitation(self):
        records = [
            make_record(
                title="Paper A",
                references=["Smith 2020", "Jones 2019"],
            ),
            make_record(
                title="Paper B",
                references=["Smith 2020", "Brown 2021"],
            ),
        ]
        engine = NetworkEngine(records)
        result = engine.co_citation(top_n=10)
        # Smith 2020 is co-cited with both Jones and Brown
        assert result.total_edges >= 1

    def test_no_references(self):
        records = [
            make_record(title="Paper A"),
            make_record(title="Paper B"),
        ]
        engine = NetworkEngine(records)
        result = engine.co_citation()
        assert result.total_edges == 0


class TestBibliographicCoupling:
    def test_reference_coupling(self):
        records = [
            make_record(
                title="Paper A",
                references=["Smith 2020", "Jones 2019"],
            ),
            make_record(
                title="Paper B",
                references=["Smith 2020", "Jones 2019"],
            ),
        ]
        engine = NetworkEngine(records)
        result = engine.bibliographic_coupling(top_n=10)
        # They share 2 references
        assert result.total_edges == 1
        assert result.graph_type == "bibliographic_coupling"

    def test_keyword_fallback(self):
        records = [
            make_record(
                title="Paper A",
                keywords=["AI", "ML"],
            ),
            make_record(
                title="Paper B",
                keywords=["AI", "DL"],
            ),
        ]
        engine = NetworkEngine(records)
        result = engine.bibliographic_coupling(top_n=10)
        # Falls back to keyword coupling since no references
        assert result.graph_type == "keyword_coupling"
        assert result.total_edges == 1


class TestExport:
    def test_csv_export(self, tmp_path):
        edges = [("A", "B", 5), ("B", "C", 3)]
        out = tmp_path / "test.csv"
        result = NetworkEngine.to_csv(edges, out)
        assert result.exists()
        content = result.read_text()
        assert "source,target,weight" in content
        assert "A,B,5" in content

    def test_gexf_export(self, tmp_path):
        edges = [("A", "B", 5)]
        nodes = [("A", 1), ("B", 1)]
        out = tmp_path / "test.gexf"
        result = NetworkEngine.to_gexf(edges, nodes, out)
        assert result.exists()

    def test_empty_export(self, tmp_path):
        edges: list = []
        out = tmp_path / "empty.csv"
        result = NetworkEngine.to_csv(edges, out)
        assert result.exists()

    def test_graphml_export(self, tmp_path):
        edges = [("A", "B", 5), ("B", "C", 3)]
        nodes = [("A", 1), ("B", 1), ("C", 1)]
        out = tmp_path / "test.graphml"
        result = NetworkEngine.to_graphml(edges, nodes, out)
        assert result.exists()
        content = result.read_text()
        assert "graphml" in content.lower() or "<graph" in content.lower()

    def test_gexf_creates_parent_directory(self, tmp_path):
        edges = [("A", "B", 5)]
        nodes = [("A", 1), ("B", 1)]
        out = tmp_path / "reports" / "subdir" / "net.gexf"
        result = NetworkEngine.to_gexf(edges, nodes, out)
        assert result.exists()
        assert out.parent.is_dir()

    def test_graphml_creates_parent_directory(self, tmp_path):
        edges = [("A", "B", 5)]
        nodes = [("A", 1), ("B", 1)]
        out = tmp_path / "reports" / "subdir" / "net.graphml"
        result = NetworkEngine.to_graphml(edges, nodes, out)
        assert result.exists()
        assert out.parent.is_dir()

    def test_gexf_no_nodes(self, tmp_path):
        """GEXF export with edges but no node metadata."""
        edges = [("X", "Y", 3)]
        out = tmp_path / "no_nodes.gexf"
        result = NetworkEngine.to_gexf(edges, None, out)
        assert result.exists()


class TestCommunityDetection:
    def test_community_detection_with_edges(self):
        """Louvain community detection with a simple graph."""
        records = [
            make_record(
                title=f"Paper {i}",
                authors=[
                    Author(full_name=f"Author {i*2}", order=1),
                    Author(full_name=f"Author {i*2+1}", order=2),
                ],
            )
            for i in range(10)
        ]
        engine = NetworkEngine(records)
        result = engine.author_collaboration(min_papers=1)
        # With 10 papers each having 2 unique authors, there should be communities
        if result.total_nodes > 1:
            assert isinstance(result.communities, dict)
