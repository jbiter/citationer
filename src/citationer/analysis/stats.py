"""Descriptive statistics engine for bibliographic records."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from citationer.models.record import Record


@dataclass
class OverviewStats:
    """Summary statistics for a collection of records."""

    total_records: int = 0
    unique_records: int = 0
    year_min: int | None = None
    year_max: int | None = None
    num_journals: int = 0
    num_authors: int = 0
    solo_rate: float = 0.0  # 独著率
    coop_rate: float = 0.0  # 合作率
    num_institutions: int = 0
    num_countries: int = 0
    language_dist: dict[str, int] = field(default_factory=dict)
    doc_type_dist: dict[str, int] = field(default_factory=dict)
    avg_citations: float = 0.0
    h_index: int = 0  # computed on citation_count


@dataclass
class YearlyStats:
    """Year-by-year publication counts."""

    year_counts: dict[int, int] = field(default_factory=dict)
    cumulative: dict[int, int] = field(default_factory=dict)
    trend_slope: float = 0.0  # linear regression slope


@dataclass
class TopList:
    """A ranked list of items with counts."""

    items: list[tuple[str, int]] = field(default_factory=list)
    total_unique: int = 0


@dataclass
class AuthorStats:
    """Author-level statistics."""

    top_authors: TopList = field(default_factory=TopList)
    core_authors: list[str] = field(default_factory=list)  # Price's Law
    solo_count: int = 0
    coop_count: int = 0
    avg_authors_per_paper: float = 0.0
    first_author_dist: list[tuple[str, int]] = field(default_factory=list)
    author_h_index: list[tuple[str, int]] = field(default_factory=list)


class StatsEngine:
    """Compute descriptive statistics on a collection of Records."""

    def __init__(self, records: list[Record]) -> None:
        self._records = records

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------

    def overview(self) -> OverviewStats:
        """Generate an overview dashboard."""
        records = self._records
        n = len(records)

        stats = OverviewStats()
        stats.total_records = n
        # Unique is the same as total after dedup (caller handles dedup first)
        stats.unique_records = n

        # Year range
        years = [r.year for r in records if r.year is not None]
        if years:
            stats.year_min = min(years)
            stats.year_max = max(years)

        # Journal count
        journals: set[str] = set()
        for r in records:
            if r.journal:
                journals.add(r.journal.lower())
        stats.num_journals = len(journals)

        # Author stats
        author_set: set[str] = set()
        solo = 0
        coop = 0
        author_counts: list[int] = []
        for r in records:
            n_auth = r.author_count
            author_counts.append(n_auth)
            for a in r.authors:
                author_set.add(a.full_name.lower())
            if n_auth == 1:
                solo += 1
            elif n_auth > 1:
                coop += 1

        stats.num_authors = len(author_set)
        if n > 0:
            stats.solo_rate = solo / n
            stats.coop_rate = coop / n

        # Institutions
        inst_set: set[str] = set()
        country_set: set[str] = set()
        for r in records:
            for inst in r.institutions:
                inst_set.add(inst.name)
                if inst.country:
                    country_set.add(inst.country)
        stats.num_institutions = len(inst_set)
        stats.num_countries = len(country_set)

        # Language distribution
        lang_dist: dict[str, int] = {}
        for r in records:
            lang = r.language or "unknown"
            lang_dist[lang] = lang_dist.get(lang, 0) + 1
        stats.language_dist = dict(sorted(lang_dist.items(), key=lambda x: -x[1]))

        # Document type distribution
        dt_dist: dict[str, int] = {}
        for r in records:
            dt = r.doc_type.value
            dt_dist[dt] = dt_dist.get(dt, 0) + 1
        stats.doc_type_dist = dict(sorted(dt_dist.items(), key=lambda x: -x[1]))

        # Citation stats
        citations = [
            r.citation_count
            for r in records
            if r.citation_count is not None and r.citation_count > 0
        ]
        if citations:
            stats.avg_citations = sum(citations) / len(citations)
            stats.h_index = self._compute_h_index(citations)

        return stats

    # ------------------------------------------------------------------
    # Yearly
    # ------------------------------------------------------------------

    def yearly(self) -> YearlyStats:
        """Yearly publication counts with cumulative and trend."""
        year_counts: dict[int, int] = defaultdict(int)
        for r in self._records:
            if r.year is not None:
                year_counts[r.year] += 1

        if not year_counts:
            return YearlyStats()

        sorted_years = sorted(year_counts)
        cumulative: dict[int, int] = {}
        total = 0
        for y in sorted_years:
            total += year_counts[y]
            cumulative[y] = total

        # Simple linear trend slope
        slope = self._trend_slope(year_counts)

        return YearlyStats(
            year_counts=dict(sorted(year_counts.items())),
            cumulative=cumulative,
            trend_slope=slope,
        )

    def yearly_by_source(self) -> dict[str, dict[int, int]]:
        """Yearly counts broken down by source database."""
        result: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        for r in self._records:
            if r.year is not None:
                result[r.source_database][r.year] += 1
        return dict(result)

    # ------------------------------------------------------------------
    # Journals
    # ------------------------------------------------------------------

    def journals(self, top_n: int = 20) -> TopList:
        """Top-N journals by publication count."""
        counter: Counter[str] = Counter()
        for r in self._records:
            if r.journal:
                counter[r.journal] += 1

        items = counter.most_common(top_n)
        return TopList(items=items, total_unique=len(counter))

    # ------------------------------------------------------------------
    # Authors
    # ------------------------------------------------------------------

    def authors(self, top_n: int = 20) -> AuthorStats:
        """Author-level analysis."""
        records = self._records

        # Author publication counts
        author_pub: Counter[str] = Counter()
        author_citations: dict[str, int] = defaultdict(int)
        first_author_pub: Counter[str] = Counter()
        paper_author_counts: list[int] = []

        for r in records:
            n_a = r.author_count
            paper_author_counts.append(n_a)

            for a in r.authors:
                name = a.full_name
                author_pub[name] += 1
                if r.citation_count:
                    author_citations[name] += r.citation_count

            if r.authors:
                first = r.authors[0]
                first_author_pub[first.full_name] += 1

        # Price's Law: core authors publish >= 0.749 * sqrt(max_pubs)
        core_authors: list[str] = []
        if author_pub:
            max_pubs = author_pub.most_common(1)[0][1]
            threshold = 0.749 * (max_pubs**0.5)
            core_authors = [
                name for name, count in author_pub.items() if count >= threshold
            ]

        # h-index per author
        author_h = self._author_h_index(records)

        return AuthorStats(
            top_authors=TopList(
                items=author_pub.most_common(top_n),
                total_unique=len(author_pub),
            ),
            core_authors=sorted(core_authors),
            solo_count=sum(1 for n in paper_author_counts if n == 1),
            coop_count=sum(1 for n in paper_author_counts if n > 1),
            avg_authors_per_paper=(
                sum(paper_author_counts) / len(paper_author_counts)
                if paper_author_counts
                else 0.0
            ),
            first_author_dist=first_author_pub.most_common(top_n),
            author_h_index=sorted(author_h.items(), key=lambda x: -x[1])[:top_n],
        )

    # ------------------------------------------------------------------
    # Institutions
    # ------------------------------------------------------------------

    def institutions(self, top_n: int = 20) -> TopList:
        """Top-N institutions by publication count."""
        counter: Counter[str] = Counter()
        for r in self._records:
            for inst in r.institutions:
                counter[inst.name] += 1

        items = counter.most_common(top_n)
        return TopList(items=items, total_unique=len(counter))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_h_index(citations: list[int]) -> int:
        """Compute h-index: h papers with at least h citations each."""
        sorted_cites = sorted(citations, reverse=True)
        h = 0
        for i, c in enumerate(sorted_cites):
            if c >= i + 1:
                h = i + 1
            else:
                break
        return h

    @staticmethod
    def _trend_slope(year_counts: dict[int, int]) -> float:
        """Simple linear regression slope."""
        if len(year_counts) < 2:
            return 0.0

        years = sorted(year_counts)
        n = len(years)
        x_mean = sum(years) / n
        y_mean = sum(year_counts[y] for y in years) / n

        num = sum(
            (y - x_mean) * (year_counts[y] - y_mean) for y in years
        )
        den = sum((y - x_mean) ** 2 for y in years)

        return num / den if den != 0 else 0.0

    @staticmethod
    def _author_h_index(records: list[Record]) -> dict[str, int]:
        """Compute h-index for all authors in the dataset."""
        author_cites: dict[str, list[int]] = defaultdict(list)
        for r in records:
            if not r.citation_count:
                continue
            for a in r.authors:
                author_cites[a.full_name].append(r.citation_count)

        return {
            name: StatsEngine._compute_h_index(cites)
            for name, cites in author_cites.items()
        }
