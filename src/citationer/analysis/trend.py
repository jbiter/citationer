"""Trend analysis engine — burst detection, strategic diagrams, etc."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from citationer.models.record import Record


@dataclass
class BurstResult:
    """A detected burst for a keyword."""

    keyword: str
    start_year: int
    end_year: int
    strength: float  # burst intensity
    years: dict[int, int] = field(default_factory=dict)


@dataclass
class StrategyTheme:
    """A theme (keyword cluster) on the strategic diagram."""

    label: str  # theme name (top keyword)
    keywords: list[str]
    centrality: float  # X-axis: external connection strength
    density: float     # Y-axis: internal cohesion
    quadrant: int      # 1=top-right(motor), 2=top-left(niche),
                       # 3=bottom-left(emerging), 4=bottom-right(basic)


@dataclass
class StrategyDiagram:
    """Strategic diagram analysis result."""

    themes: list[StrategyTheme] = field(default_factory=list)
    centrality_median: float = 0.0
    density_median: float = 0.0


@dataclass
class BurstAnalysis:
    """Complete burst detection analysis."""

    bursts: list[BurstResult] = field(default_factory=list)
    total_keywords_analyzed: int = 0


class TrendEngine:
    """Trend analysis engine."""

    def __init__(self, records: list[Record]) -> None:
        self._records = records

    # ------------------------------------------------------------------
    # Burst detection (simplified Kleinberg algorithm)
    # ------------------------------------------------------------------

    def hotspots(
        self,
        top_n: int = 30,
        gamma: float = 1.0,
        min_years: int = 2,
    ) -> BurstAnalysis:
        """Detect keyword bursts using a simplified Kleinberg algorithm.

        For each keyword, the algorithm models yearly frequencies as a
        two-state automaton (baseline / burst).  A burst is reported when
        the keyword exceeds its baseline rate for *min_years* consecutive
        years.

        Args:
            top_n: Only analyze the top-N most frequent keywords.
            gamma: Burst sensitivity (lower = more sensitive).
            min_years: Minimum consecutive years to qualify as a burst.
        """
        # ── Build keyword × year frequency matrix ──────────────
        kw_years: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        kw_total: dict[str, int] = defaultdict(int)

        for r in self._records:
            year = r.year
            if year is None:
                continue
            all_kw = list(r.keywords)
            if r.keywords_en:
                all_kw.extend(r.keywords_en)
            for kw in all_kw:
                kw = kw.strip()
                if len(kw) >= 2:
                    kw_years[kw][year] += 1
                    kw_total[kw] += 1

        # Top-N keywords by total frequency
        top_kw = sorted(kw_total.items(), key=lambda x: -x[1])[:top_n]

        # ── Detect bursts for each top keyword ────────────────
        bursts: list[BurstResult] = []

        for kw, _ in top_kw:
            yearly = kw_years[kw]
            if len(yearly) < 3:
                continue

            years = sorted(yearly)
            counts = [yearly[y] for y in years]

            # Compute baseline (median of non-zero years)
            nonzero = [c for c in counts if c > 0]
            if not nonzero:
                continue
            baseline = sorted(nonzero)[len(nonzero) // 2]

            # Detect burst periods: consecutive years where count
            # exceeds baseline * gamma
            in_burst = False
            burst_start = 0
            burst_years: dict[int, int] = {}

            for y, c in zip(years, counts):
                threshold = baseline * gamma
                if c > threshold and c >= 2:
                    if not in_burst:
                        in_burst = True
                        burst_start = y
                        burst_years = {}
                    burst_years[y] = c
                else:
                    if in_burst and len(burst_years) >= min_years:
                        # Compute burst strength
                        avg_count = sum(burst_years.values()) / max(len(burst_years), 1)
                        strength = avg_count / max(baseline, 1)
                        bursts.append(BurstResult(
                            keyword=kw,
                            start_year=burst_start,
                            end_year=y - 1,
                            strength=round(strength, 2),
                            years=dict(burst_years),
                        ))
                    in_burst = False

            # Close trailing burst
            if in_burst and len(burst_years) >= min_years:
                avg_count = sum(burst_years.values()) / max(len(burst_years), 1)
                strength = avg_count / max(baseline, 1)
                bursts.append(BurstResult(
                    keyword=kw,
                    start_year=burst_start,
                    end_year=years[-1],
                    strength=round(strength, 2),
                    years=dict(burst_years),
                ))

        # Sort by strength descending
        bursts.sort(key=lambda b: -b.strength)

        return BurstAnalysis(
            bursts=bursts,
            total_keywords_analyzed=len(top_kw),
        )

    # ------------------------------------------------------------------
    # Strategic diagram
    # ------------------------------------------------------------------

    def strategy(self, top_n: int = 50) -> StrategyDiagram:
        """Build a strategic diagram from keyword co-occurrence clusters.

        Uses Louvain community detection on the keyword co-occurrence
        network, then computes centrality (between-cluster links) and
        density (within-cluster cohesion) for each theme cluster.
        """
        # ── Build keyword co-occurrence matrix ──────────────────
        kw_counter: dict[str, int] = defaultdict(int)
        pair_counter: dict[tuple[str, str], int] = defaultdict(int)

        for r in self._records:
            all_kw = list(r.keywords)
            if r.keywords_en:
                all_kw.extend(r.keywords_en)
            kws = [k.strip() for k in all_kw if len(k.strip()) >= 2]
            for kw in kws:
                kw_counter[kw] += 1
            for i in range(len(kws)):
                for j in range(i + 1, len(kws)):
                    x, y = kws[i], kws[j]
                    if x < y:
                        pair_counter[(x, y)] += 1
                    else:
                        pair_counter[(y, x)] += 1

        # Top-N keywords
        top_set = {kw for kw, _ in sorted(
            kw_counter.items(), key=lambda x: -x[1]
        )[:top_n]}

        # ── Build network and detect communities ────────────────
        try:
            import networkx as nx
            from networkx.algorithms.community import louvain_communities
        except ImportError:
            return StrategyDiagram()

        g = nx.Graph()
        for (a, b), w in pair_counter.items():
            if a in top_set and b in top_set:
                g.add_edge(a, b, weight=w)

        if not g.edges():
            return StrategyDiagram()

        try:
            communities_list = louvain_communities(g, seed=42)
        except Exception:
            return StrategyDiagram()

        communities = []
        for c in communities_list:
            communities.append(set(c))

        # ── Compute centrality & density per cluster ────────────
        themes: list[StrategyTheme] = []
        all_centralities: list[float] = []
        all_densities: list[float] = []

        for ci, cluster in enumerate(communities):
            if len(cluster) < 2:
                continue

            # Density: average edge weight within the cluster
            internal_edges = 0
            internal_weight = 0
            cluster_list = list(cluster)
            for ai in range(len(cluster_list)):
                for bi in range(ai + 1, len(cluster_list)):
                    ka, kb = cluster_list[ai], cluster_list[bi]
                    key = (ka, kb) if ka < kb else (kb, ka)
                    w = pair_counter.get(key, 0)
                    if w > 0:
                        internal_edges += 1
                        internal_weight += w
            density = (internal_weight / internal_edges) if internal_edges > 0 else 0

            # Centrality: average co-occurrence with keywords outside the cluster
            external_weight = 0
            external_count = 0
            for kw in cluster:
                # All co-occurrences of this keyword
                for other_kw in top_set:
                    if other_kw in cluster or other_kw == kw:
                        continue
                    key = (kw, other_kw) if kw < other_kw else (other_kw, kw)
                    w = pair_counter.get(key, 0)
                    if w > 0:
                        external_weight += w
                        external_count += 1
            centrality = (external_weight / external_count) if external_count > 0 else 0

            # Top keyword as theme label
            top_kw = max(cluster, key=lambda k: kw_counter.get(k, 0))
            keywords = sorted(cluster, key=lambda k: -kw_counter.get(k, 0))[:5]

            all_centralities.append(centrality)
            all_densities.append(density)

        # Determine quadrant boundaries (medians)
        if all_centralities and all_densities:
            c_med = sorted(all_centralities)[len(all_centralities) // 2]
            d_med = sorted(all_densities)[len(all_densities) // 2]

            for ci, cluster in enumerate(communities):
                if len(cluster) < 2:
                    continue

                # Recompute (we lost the computed values in the loop above)
                cluster_list = list(cluster)
                internal_edges = 0
                internal_weight = 0
                for ai in range(len(cluster_list)):
                    for bi in range(ai + 1, len(cluster_list)):
                        ka, kb = cluster_list[ai], cluster_list[bi]
                        key = (ka, kb) if ka < kb else (kb, ka)
                        w = pair_counter.get(key, 0)
                        if w > 0:
                            internal_edges += 1
                            internal_weight += w
                density = (internal_weight / internal_edges) if internal_edges > 0 else 0

                external_weight = 0
                external_count = 0
                for kw in cluster:
                    for other_kw in top_set:
                        if other_kw in cluster or other_kw == kw:
                            continue
                        key = (kw, other_kw) if kw < other_kw else (other_kw, kw)
                        w = pair_counter.get(key, 0)
                        if w > 0:
                            external_weight += w
                            external_count += 1
                centrality = (external_weight / external_count) if external_count > 0 else 0

                # Quadrant
                if centrality >= c_med and density >= d_med:
                    quadrant = 1  # Motor
                elif centrality < c_med and density >= d_med:
                    quadrant = 2  # Niche
                elif centrality < c_med and density < d_med:
                    quadrant = 3  # Emerging/Declining
                else:
                    quadrant = 4  # Basic

                top_kw = max(cluster, key=lambda k: kw_counter.get(k, 0))
                keywords = sorted(cluster, key=lambda k: -kw_counter.get(k, 0))[:5]

                themes.append(StrategyTheme(
                    label=top_kw,
                    keywords=keywords,
                    centrality=round(centrality, 3),
                    density=round(density, 3),
                    quadrant=quadrant,
                ))

            themes.sort(key=lambda t: -t.density)

            return StrategyDiagram(
                themes=themes,
                centrality_median=round(c_med, 3),
                density_median=round(d_med, 3),
            )

        return StrategyDiagram()
