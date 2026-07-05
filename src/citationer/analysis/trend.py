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
