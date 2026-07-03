"""Network analysis engine for bibliographic records.

Provides keyword co-occurrence, author/institution collaboration,
co-citation, and bibliographic coupling analysis.
All graph methods return NetworkX Graph objects + metadata dataclasses.
Export to GEXF, GraphML, CSV, and interactive Plotly HTML.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from citationer.models.record import Record


@dataclass
class CoOccurrenceMatrix:
    """Keyword co-occurrence analysis result."""

    keywords: list[str] = field(default_factory=list)
    edges: list[tuple[str, str, int]] = field(default_factory=list)
    total_keywords: int = 0
    total_edges: int = 0


@dataclass
class CollaborationGraph:
    """Author/institution collaboration network result."""

    collab_type: str = "authors"  # "authors" or "institutions"
    nodes: list[tuple[str, int]] = field(default_factory=list)  # (name, paper_count)
    edges: list[tuple[str, str, int]] = field(default_factory=list)  # (a, b, weight)
    communities: dict[str, int] = field(default_factory=dict)  # node → community_id
    total_nodes: int = 0
    total_edges: int = 0


@dataclass
class CitationGraph:
    """Co-citation or bibliographic coupling result."""

    graph_type: str = "cocitation"
    edges: list[tuple[str, str, int]] = field(default_factory=list)
    total_edges: int = 0


class NetworkEngine:
    """Network analysis engine for bibliographic record collections."""

    def __init__(self, records: list[Record]) -> None:
        self._records = records

    # ------------------------------------------------------------------
    # Keyword co-occurrence
    # ------------------------------------------------------------------

    def keyword_cooccurrence(
        self,
        top_n: int = 50,
        threshold: int = 3,
    ) -> CoOccurrenceMatrix:
        """Build a keyword co-occurrence network.

        Args:
            top_n: Only include the top-N most frequent keywords.
            threshold: Minimum co-occurrence count for an edge.
        """
        # Count keyword frequencies
        kw_counter: Counter[str] = Counter()
        for r in self._records:
            all_kw = list(r.keywords)
            if r.keywords_en:
                all_kw.extend(r.keywords_en)
            for kw in all_kw:
                kw_clean = kw.strip()
                if kw_clean and len(kw_clean) >= 2:
                    kw_counter[kw_clean] += 1

        # Top-N keywords
        top_keywords = {kw for kw, _ in kw_counter.most_common(top_n)}

        # Count co-occurrences
        pair_counter: Counter[tuple[str, str]] = Counter()
        for r in self._records:
            all_kw = list(r.keywords)
            if r.keywords_en:
                all_kw.extend(r.keywords_en)
            record_kw = [
                kw.strip() for kw in all_kw
                if kw.strip() in top_keywords
            ]
            # Every pair of keywords in this record co-occurs
            for i in range(len(record_kw)):
                for j in range(i + 1, len(record_kw)):
                    a, b = record_kw[i], record_kw[j]
                    if a < b:
                        pair_counter[(a, b)] += 1
                    else:
                        pair_counter[(b, a)] += 1

        # Filter by threshold
        edges = [
            (a, b, w) for (a, b), w in pair_counter.items()
            if w >= threshold
        ]
        edges.sort(key=lambda x: -x[2])

        return CoOccurrenceMatrix(
            keywords=sorted(top_keywords),
            edges=edges,
            total_keywords=len(top_keywords),
            total_edges=len(edges),
        )

    # ------------------------------------------------------------------
    # Author collaboration
    # ------------------------------------------------------------------

    def author_collaboration(
        self,
        min_papers: int = 2,
        collab_type: str = "authors",
    ) -> CollaborationGraph:
        """Build an author (or institution) collaboration network.

        Args:
            min_papers: Minimum papers for an author/institution to be included.
            collab_type: "authors" or "institutions".
        """
        if collab_type == "institutions":
            return self._institution_collaboration(min_papers)

        # Count author publications
        author_papers: Counter[str] = Counter()
        author_pairs: Counter[tuple[str, str]] = Counter()

        for r in self._records:
            names = [
                a.full_name.strip() for a in r.authors
                if a.full_name.strip()
            ]
            for name in names:
                author_papers[name] += 1
            # Count all pairs in this paper as collaborations
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    a, b = names[i], names[j]
                    pair = (a, b) if a < b else (b, a)
                    author_pairs[pair] += 1

        # Filter by min_papers
        active_authors = {
            name for name, count in author_papers.items()
            if count >= min_papers
        }

        edges = [
            (a, b, w)
            for (a, b), w in author_pairs.items()
            if a in active_authors and b in active_authors
        ]
        edges.sort(key=lambda x: -x[2])

        nodes = [
            (name, author_papers[name])
            for name in active_authors
        ]
        nodes.sort(key=lambda x: -x[1])

        # Community detection
        communities = self._detect_communities(
            [(a, b) for a, b, _ in edges], active_authors
        )

        return CollaborationGraph(
            collab_type="authors",
            nodes=nodes,
            edges=edges,
            communities=communities,
            total_nodes=len(active_authors),
            total_edges=len(edges),
        )

    def _institution_collaboration(
        self, min_papers: int = 2
    ) -> CollaborationGraph:
        """Build an institution collaboration network."""
        inst_counter: Counter[str] = Counter()
        inst_pairs: Counter[tuple[str, str]] = Counter()

        for r in self._records:
            names = [
                inst.name.strip() for inst in r.institutions
                if inst.name.strip()
            ]
            for name in names:
                inst_counter[name] += 1
            for i in range(len(names)):
                for j in range(i + 1, len(names)):
                    a, b = names[i], names[j]
                    pair = (a, b) if a < b else (b, a)
                    inst_pairs[pair] += 1

        active_insts = {
            name for name, count in inst_counter.items()
            if count >= min_papers
        }

        edges = [
            (a, b, w)
            for (a, b), w in inst_pairs.items()
            if a in active_insts and b in active_insts
        ]
        edges.sort(key=lambda x: -x[2])

        nodes = [
            (name, inst_counter[name]) for name in active_insts
        ]
        nodes.sort(key=lambda x: -x[1])

        communities = self._detect_communities(
            [(a, b) for a, b, _ in edges], active_insts
        )

        return CollaborationGraph(
            collab_type="institutions",
            nodes=nodes,
            edges=edges,
            communities=communities,
            total_nodes=len(active_insts),
            total_edges=len(edges),
        )

    # ------------------------------------------------------------------
    # Co-citation
    # ------------------------------------------------------------------

    def co_citation(self, top_n: int = 30) -> CitationGraph:
        """Co-citation analysis: two references cited together in the same paper.

        Requires record.references to be populated (WoS exports include this;
        CNKI exports typically do not).
        """
        ref_pairs: Counter[tuple[str, str]] = Counter()

        for r in self._records:
            refs = r.references
            if not refs:
                continue
            # Each pair of references in this paper is a co-citation
            for i in range(len(refs)):
                for j in range(i + 1, len(refs)):
                    a, b = refs[i].strip(), refs[j].strip()
                    if not a or not b:
                        continue
                    pair = (a, b) if a < b else (b, a)
                    ref_pairs[pair] += 1

        top_pairs = ref_pairs.most_common(top_n)
        edges = [(a, b, w) for (a, b), w in top_pairs]

        return CitationGraph(
            graph_type="cocitation",
            edges=edges,
            total_edges=len(edges),
        )

    # ------------------------------------------------------------------
    # Bibliographic coupling
    # ------------------------------------------------------------------

    def bibliographic_coupling(self, top_n: int = 30) -> CitationGraph:
        """Bibliographic coupling: two papers that share references.

        Falls back to keyword-based coupling if reference data is unavailable.
        """
        # First attempt: reference-based coupling
        paper_refs: list[set[str]] = []
        has_refs = False
        for r in self._records:
            if r.references:
                paper_refs.append({ref.strip() for ref in r.references if ref.strip()})
                has_refs = True
            else:
                paper_refs.append(set())

        if not has_refs:
            return self._keyword_coupling(top_n)

        # Count shared references between papers
        pair_counter: Counter[tuple[int, int]] = Counter()
        n = len(paper_refs)
        for i in range(n):
            if not paper_refs[i]:
                continue
            for j in range(i + 1, n):
                if not paper_refs[j]:
                    continue
                shared = len(paper_refs[i] & paper_refs[j])
                if shared > 0:
                    pair_counter[(i, j)] = shared

        top_pairs = pair_counter.most_common(top_n)
        edges = [
            (
                self._records[i].title[:80],
                self._records[j].title[:80],
                w,
            )
            for (i, j), w in top_pairs
        ]

        return CitationGraph(
            graph_type="bibliographic_coupling",
            edges=edges,
            total_edges=len(edges),
        )

    def _keyword_coupling(self, top_n: int = 30) -> CitationGraph:
        """Fallback: keyword-based bibliographic coupling."""
        paper_kw: list[set[str]] = []
        for r in self._records:
            kw_set = set(r.keywords)
            if r.keywords_en:
                kw_set.update(r.keywords_en)
            paper_kw.append({k.strip().lower() for k in kw_set if k.strip()})

        pair_counter: Counter[tuple[int, int]] = Counter()
        n = len(paper_kw)
        for i in range(n):
            if not paper_kw[i]:
                continue
            for j in range(i + 1, n):
                if not paper_kw[j]:
                    continue
                shared = len(paper_kw[i] & paper_kw[j])
                if shared > 0:
                    pair_counter[(i, j)] = shared

        top_pairs = pair_counter.most_common(top_n)
        edges = [
            (
                self._records[i].title[:80],
                self._records[j].title[:80],
                w,
            )
            for (i, j), w in top_pairs
        ]

        return CitationGraph(
            graph_type="keyword_coupling",
            edges=edges,
            total_edges=len(edges),
        )

    # ------------------------------------------------------------------
    # Community detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_communities(
        edges: list[tuple[str, str]],
        nodes: set[str],
    ) -> dict[str, int]:
        """Detect communities in a graph using Louvain algorithm.

        Returns a dict mapping node name → community ID.
        """
        try:
            import networkx as nx
            from networkx.algorithms.community import louvain_communities
        except ImportError:
            return {}

        if not edges:
            return {}

        g = nx.Graph()
        g.add_nodes_from(nodes)
        g.add_edges_from(edges)

        try:
            communities_list = louvain_communities(g, seed=42)
            result: dict[str, int] = {}
            for cid, community in enumerate(communities_list):
                for node in community:
                    result[node] = cid
            return result
        except (ValueError, RuntimeError):
            return {}

    # ------------------------------------------------------------------
    # Export methods
    # ------------------------------------------------------------------

    @staticmethod
    def to_gexf(
        edges: list[tuple[str, str, int]],
        nodes: list[tuple[str, int]] | None,
        output_path: Path,
    ) -> Path:
        """Export a graph to GEXF format."""
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("networkx is required for GEXF export.")

        g = nx.Graph()
        if nodes:
            for name, weight in nodes:
                g.add_node(name, weight=weight)
        for a, b, w in edges:
            g.add_edge(a, b, weight=w)

        nx.write_gexf(g, str(output_path))
        return output_path

    @staticmethod
    def to_graphml(
        edges: list[tuple[str, str, int]],
        nodes: list[tuple[str, int]] | None,
        output_path: Path,
    ) -> Path:
        """Export a graph to GraphML format."""
        try:
            import networkx as nx
        except ImportError:
            raise ImportError("networkx is required for GraphML export.")

        g = nx.Graph()
        if nodes:
            for name, weight in nodes:
                g.add_node(name, weight=weight)
        for a, b, w in edges:
            g.add_edge(a, b, weight=w)

        nx.write_graphml(g, str(output_path))
        return output_path

    @staticmethod
    def to_csv(
        edges: list[tuple[str, str, int]],
        output_path: Path,
    ) -> Path:
        """Export edge list to CSV format."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["source", "target", "weight"])
            for a, b, w in edges:
                writer.writerow([a, b, w])
        return output_path

    @staticmethod
    def to_html(
        edges: list[tuple[str, str, int]],
        nodes: list[tuple[str, int]] | None,
        communities: dict[str, int] | None,
        output_path: Path,
        title: str = "Citation Network",
    ) -> Path:
        """Generate an interactive Plotly HTML network visualization."""
        try:
            import networkx as nx
            import plotly.graph_objects as go
        except ImportError as e:
            raise ImportError(
                "networkx and plotly are required for HTML export."
            ) from e

        g = nx.Graph()
        if nodes:
            for name, weight in nodes:
                g.add_node(name, weight=weight)
        for a, b, w in edges:
            g.add_edge(a, b, weight=w)

        if not g.nodes:
            raise ValueError("Empty graph — nothing to visualize")

        # Layout
        pos = nx.spring_layout(g, k=1.5, seed=42, iterations=50)

        # Edges
        edge_x: list[float | None] = []
        edge_y: list[float | None] = []
        for u, v in g.edges():
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            line={"width": 0.5, "color": "#888"},
            hoverinfo="none",
            mode="lines",
        )

        # Nodes
        node_x: list[float] = []
        node_y: list[float] = []
        node_text: list[str] = []
        node_color: list[str] = []
        node_size: list[float] = []

        # Color palette for communities
        colors = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
            "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
            "#bcbd22", "#17becf",
        ]

        for node in g.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(node)
            # Color by community
            if communities and node in communities:
                cid = communities[node] % len(colors)
                node_color.append(colors[cid])
            else:
                node_color.append(colors[0])
            # Size by degree
            node_size.append(10 + 5 * g.degree(node))

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers+text",
            hoverinfo="text",
            text=node_text,
            textposition="top center",
            marker={
                "color": node_color,
                "size": node_size,
                "line": {"width": 1, "color": "#333"},
            },
        )

        fig = go.Figure(
            data=[edge_trace, node_trace],
            layout=go.Layout(
                title=title,
                showlegend=False,
                hovermode="closest",
                margin={"b": 20, "l": 5, "r": 5, "t": 40},
                xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
                yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            ),
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.write_html(str(output_path))
        return output_path
