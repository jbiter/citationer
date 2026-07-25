"""Multi-dataset comparison engine (P5-1).

Provides in-memory comparison of two or more record collections, grouped by
``source_database`` or ``source_file``.  Reuses existing ``StatsEngine``,
``TrendEngine``, ``TextEngine``, and the dedup title-similarity helper.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations

from citationer.analysis.dedup import _title_similarity
from citationer.analysis.network import NetworkEngine
from citationer.analysis.stats import StatsEngine
from citationer.models.record import Record


@dataclass
class DatasetOverview:
    """High-level statistics for a single dataset."""

    name: str
    total_records: int = 0
    year_min: int | None = None
    year_max: int | None = None
    top_journals: list[tuple[str, int]] = field(default_factory=list)
    top_authors: list[tuple[str, int]] = field(default_factory=list)
    top_keywords: list[tuple[str, int]] = field(default_factory=list)
    unique_journals: int = 0
    unique_authors: int = 0
    unique_keywords: int = 0


@dataclass
class OverlapResult:
    """Pairwise overlap between two datasets."""

    dataset_a: str
    dataset_b: str
    doi_overlap: int = 0
    title_overlap: int = 0
    keyword_jaccard: float = 0.0
    shared_authors: list[tuple[str, int]] = field(default_factory=list)
    shared_institutions: list[tuple[str, int]] = field(default_factory=list)


@dataclass
class TrendComparison:
    """Yearly publication trends across datasets."""

    year_min: int | None = None
    year_max: int | None = None
    year_counts: dict[str, dict[int, int]] = field(default_factory=dict)
    slopes: dict[str, float] = field(default_factory=dict)


@dataclass
class TopicComparison:
    """Keyword / topic overlap across datasets."""

    dataset_keywords: dict[str, list[tuple[str, int]]] = field(default_factory=dict)
    pairwise_jaccard: dict[tuple[str, str], float] = field(default_factory=dict)
    shared_keywords: dict[tuple[str, str], list[str]] = field(default_factory=dict)


@dataclass
class NetworkComparison:
    """Author / institution network overlap across datasets."""

    collab_type: str = "authors"
    shared_nodes: dict[str, list[tuple[str, int]]] = field(default_factory=dict)
    cross_edges: list[tuple[str, str, int]] = field(default_factory=list)
    dataset_node_counts: dict[str, int] = field(default_factory=dict)


class CompareEngine:
    """Compare multiple in-memory record collections."""

    def __init__(self, records: list[Record], *, by: str = "database") -> None:
        self._records = records
        self._groups = _group_records(records, by=by)

    @property
    def dataset_names(self) -> list[str]:
        return sorted(self._groups)

    @property
    def groups(self) -> dict[str, list[Record]]:
        return self._groups

    def overview(
        self, top_n: int = 10, threshold: float = 0.85
    ) -> tuple[dict[str, DatasetOverview], list[OverlapResult]]:
        """Per-dataset overviews and pairwise overlaps."""
        overviews = {
            name: _dataset_overview(name, recs, top_n)
            for name, recs in self._groups.items()
        }
        overlaps = []
        for a, b in combinations(self._groups, 2):
            overlaps.append(
                _pairwise_overlap(
                    a, self._groups[a], b, self._groups[b], threshold
                )
            )
        return overviews, overlaps

    def trends(self) -> TrendComparison:
        """Side-by-side yearly trends."""
        year_counts: dict[str, dict[int, int]] = {}
        slopes: dict[str, float] = {}
        years: list[int] = []
        for name, recs in self._groups.items():
            stats = StatsEngine(recs).yearly()
            year_counts[name] = dict(stats.year_counts)
            slopes[name] = float(stats.trend_slope)
            years.extend(year_counts[name])
        return TrendComparison(
            year_min=min(years) if years else None,
            year_max=max(years) if years else None,
            year_counts=year_counts,
            slopes=slopes,
        )

    def topics(self, top_n: int = 20) -> TopicComparison:
        """Keyword overlap across datasets."""
        dataset_keywords: dict[str, list[tuple[str, int]]] = {}
        keyword_sets: dict[str, set[str]] = {}
        for name, recs in self._groups.items():
            counter: Counter[str] = Counter()
            for r in recs:
                counter.update(r.keyword_set)
            dataset_keywords[name] = counter.most_common(top_n)
            keyword_sets[name] = set(counter)

        pairwise_jaccard: dict[tuple[str, str], float] = {}
        shared_keywords: dict[tuple[str, str], list[str]] = {}
        for a, b in combinations(keyword_sets, 2):
            sa, sb = keyword_sets[a], keyword_sets[b]
            union = sa | sb
            pairwise_jaccard[(a, b)] = (
                len(sa & sb) / len(union) if union else 0.0
            )
            shared_keywords[(a, b)] = sorted(sa & sb)

        return TopicComparison(
            dataset_keywords=dataset_keywords,
            pairwise_jaccard=pairwise_jaccard,
            shared_keywords=shared_keywords,
        )

    def network(
        self, collab_type: str = "authors", min_papers: int = 2
    ) -> NetworkComparison:
        """Shared authors/institutions and cross-dataset collaboration edges."""
        node_to_datasets: dict[str, set[str]] = defaultdict(set)
        node_counts: Counter[str] = Counter()
        for name, recs in self._groups.items():
            for r in recs:
                nodes = _record_nodes(r, collab_type)
                for node in nodes:
                    node_to_datasets[node].add(name)
                    node_counts[node] += 1

        # shared nodes: present in more than one dataset
        shared_nodes: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for node, datasets in node_to_datasets.items():
            if len(datasets) > 1:
                for ds in sorted(datasets):
                    shared_nodes[ds].append((node, node_counts[node]))

        # node counts per dataset
        dataset_node_counts: dict[str, int] = {
            name: len({n for n, dsets in node_to_datasets.items() if name in dsets})
            for name in self._groups
        }

        # cross edges via NetworkEngine over all records
        cross_edges: list[tuple[str, str, int]] = []
        try:
            engine = NetworkEngine(self._records)
            if collab_type == "institutions":
                graph = engine.author_collaboration(
                    min_papers=min_papers, collab_type="institutions"
                )
            else:
                graph = engine.author_collaboration(min_papers=min_papers)
            for a, b, w in graph.edges:
                da = node_to_datasets.get(a, set())
                db = node_to_datasets.get(b, set())
                if da and db and not (da == db):
                    cross_edges.append((a, b, w))
        except Exception:
            # networkx / optional deps may be missing; return node-level data only
            pass

        return NetworkComparison(
            collab_type=collab_type,
            shared_nodes=dict(shared_nodes),
            cross_edges=cross_edges,
            dataset_node_counts=dataset_node_counts,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _group_records(
    records: list[Record], *, by: str = "database"
) -> dict[str, list[Record]]:
    """Group records by source_database (splitting composites on '+') or source_file."""
    groups: dict[str, list[Record]] = defaultdict(list)
    for r in records:
        if by == "file":
            keys = [r.source_file] if r.source_file else []
        else:
            keys = [k.strip() for k in r.source_database.split("+") if k.strip()]
        for key in keys:
            groups[key].append(r)
    return dict(groups)


def _dataset_overview(
    name: str, records: list[Record], top_n: int
) -> DatasetOverview:
    """Build a DatasetOverview from a record list."""
    years = [r.year for r in records if r.year is not None]

    journal_counter: Counter[str] = Counter()
    author_counter: Counter[str] = Counter()
    keyword_counter: Counter[str] = Counter()
    for r in records:
        if r.journal:
            journal_counter[r.journal] += 1
        for a in r.authors:
            author_counter[a.full_name] += 1
        keyword_counter.update(r.keyword_set)

    return DatasetOverview(
        name=name,
        total_records=len(records),
        year_min=min(years) if years else None,
        year_max=max(years) if years else None,
        top_journals=journal_counter.most_common(top_n),
        top_authors=author_counter.most_common(top_n),
        top_keywords=keyword_counter.most_common(top_n),
        unique_journals=len(journal_counter),
        unique_authors=len(author_counter),
        unique_keywords=len(keyword_counter),
    )


def _pairwise_overlap(
    name_a: str,
    records_a: list[Record],
    name_b: str,
    records_b: list[Record],
    threshold: float,
) -> OverlapResult:
    """Compute overlap metrics between two record collections."""
    # DOI overlap
    doi_a = {r.doi.lower() for r in records_a if r.doi}
    doi_b = {r.doi.lower() for r in records_b if r.doi}
    doi_overlap = len(doi_a & doi_b)

    # Fuzzy title overlap
    title_overlap = _fuzzy_title_overlap(records_a, records_b, threshold)

    # Keyword Jaccard
    kw_a: set[str] = set()
    kw_b: set[str] = set()
    for r in records_a:
        kw_a.update(r.keyword_set)
    for r in records_b:
        kw_b.update(r.keyword_set)
    union = kw_a | kw_b
    keyword_jaccard = len(kw_a & kw_b) / len(union) if union else 0.0

    # Shared authors / institutions
    author_counter_a: Counter[str] = Counter()
    inst_counter_a: Counter[str] = Counter()
    for r in records_a:
        for a in r.authors:
            author_counter_a[a.full_name] += 1
        for inst in r.institutions:
            inst_counter_a[inst.name] += 1

    author_counter_b: Counter[str] = Counter()
    inst_counter_b: Counter[str] = Counter()
    for r in records_b:
        for a in r.authors:
            author_counter_b[a.full_name] += 1
        for inst in r.institutions:
            inst_counter_b[inst.name] += 1

    shared_authors = _shared_counter_items(author_counter_a, author_counter_b)
    shared_institutions = _shared_counter_items(inst_counter_a, inst_counter_b)

    return OverlapResult(
        dataset_a=name_a,
        dataset_b=name_b,
        doi_overlap=doi_overlap,
        title_overlap=title_overlap,
        keyword_jaccard=keyword_jaccard,
        shared_authors=shared_authors,
        shared_institutions=shared_institutions,
    )


def _fuzzy_title_overlap(
    records_a: list[Record], records_b: list[Record], threshold: float
) -> int:
    """Count fuzzy title matches between two record collections."""
    matched_b: set[int] = set()
    count = 0
    for ra in records_a:
        if not ra.title:
            continue
        best_idx = -1
        best_score = 0.0
        for i, rb in enumerate(records_b):
            if i in matched_b or not rb.title:
                continue
            score = _title_similarity(ra.title, rb.title, threshold=threshold)
            if score > best_score:
                best_score = score
                best_idx = i
        if best_score >= threshold and best_idx not in matched_b:
            matched_b.add(best_idx)
            count += 1
    return count


def _shared_counter_items(
    a: Counter[str], b: Counter[str], top_n: int = 20
) -> list[tuple[str, int]]:
    """Return shared keys with the minimum count in either counter."""
    shared = []
    for key in a:
        if key in b:
            shared.append((key, min(a[key], b[key])))
    shared.sort(key=lambda x: -x[1])
    return shared[:top_n]


def _record_nodes(r: Record, collab_type: str) -> set[str]:
    """Return the set of node names for a record (authors or institutions)."""
    if collab_type == "institutions":
        return {inst.name for inst in r.institutions if inst.name}
    return {a.full_name for a in r.authors if a.full_name}
