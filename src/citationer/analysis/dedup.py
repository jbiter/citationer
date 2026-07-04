"""Deduplication engine for bibliographic records.

Implements a 4-layer strict deduplication strategy:
  Layer 1: DOI exact match → auto-merge
  Layer 2: Title fuzzy match (>= 85%) + same year → auto-merge
  Layer 3: Title fuzzy match (>= 70%) + same first author + same year → flag for review
  Layer 4: Cross-language (CN+EN) matching via DOI or author+year+journal+pages
"""

from __future__ import annotations

import re
from collections.abc import Callable
from difflib import SequenceMatcher

from citationer.models.record import Record


def _normalize_title(title: str) -> str:
    """Normalize a title for comparison:
    - lowercase
    - remove punctuation
    - collapse whitespace
    - strip
    """
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def _title_similarity(title1: str, title2: str) -> float:
    """Calculate title similarity using SequenceMatcher on normalized titles."""
    t1 = _normalize_title(title1)
    t2 = _normalize_title(title2)
    if not t1 or not t2:
        return 0.0
    return SequenceMatcher(None, t1, t2).ratio()


def _merge_records(r1: Record, r2: Record) -> Record:
    """Merge two records, taking the union of their fields.

    r1 is considered the primary (kept) record.
    Fields from r2 fill in gaps in r1.
    """
    merged = r1.model_copy(deep=True)

    # Merge simple fields: prefer non-empty from r2 if r1 is empty
    simple_fields = [
        "title_en",
        "journal",
        "journal_en",
        "volume",
        "issue",
        "pages",
        "doi",
        "issn",
        "abstract",
        "abstract_en",
        "language",
    ]
    for field in simple_fields:
        v1 = getattr(merged, field)
        v2 = getattr(r2, field)
        if not v1 and v2:
            setattr(merged, field, v2)

    # Merge keywords (union)
    merged.keywords = list(dict.fromkeys(merged.keywords + r2.keywords))
    if merged.keywords_en or r2.keywords_en:
        kw_en = (merged.keywords_en or []) + (r2.keywords_en or [])
        merged.keywords_en = list(dict.fromkeys(kw_en))

    # Merge authors (keep unique by full_name)
    existing_names = {a.full_name.lower() for a in merged.authors}
    for a in r2.authors:
        if a.full_name.lower() not in existing_names:
            merged.authors.append(a)
            existing_names.add(a.full_name.lower())

    # Merge institutions
    existing_insts = {i.name for i in merged.institutions}
    for inst in r2.institutions:
        if inst.name not in existing_insts:
            merged.institutions.append(inst)
            existing_insts.add(inst.name)

    # Merge funding
    if merged.funding or r2.funding:
        funds = list(dict.fromkeys((merged.funding or []) + (r2.funding or [])))
        merged.funding = funds

    # Take the higher citation count
    c1 = merged.citation_count or 0
    c2 = r2.citation_count or 0
    if c2 > c1:
        merged.citation_count = c2

    # Prefer non-UNKNOWN doc_type
    from citationer.models.record import DocType

    if merged.doc_type == DocType.UNKNOWN and r2.doc_type != DocType.UNKNOWN:
        merged.doc_type = r2.doc_type

    # Update source tracking
    if r2.source_database:
        existing = merged.source_database.split("+") if merged.source_database else []
        if r2.source_database not in existing:
            merged.source_database = (
                f"{merged.source_database}+{r2.source_database}"
                if merged.source_database
                else r2.source_database
            )

    # Preserve both raw_data
    merged.raw_data = {**r1.raw_data, **r2.raw_data}

    return merged


class DedupEngine:
    """Multi-layer deduplication engine for bibliographic records."""

    def __init__(
        self,
        title_threshold_high: float = 0.85,
        title_threshold_low: float = 0.70,
    ) -> None:
        self.title_threshold_high = title_threshold_high
        self.title_threshold_low = title_threshold_low
        self._merge_log: list[dict] = []

    def deduplicate(
        self,
        records: list[Record],
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> tuple[list[Record], list[dict]]:
        """Run all deduplication layers.

        If *progress_callback* is provided it is called as
        ``callback(step: int, total: int)`` after each layer.

        Returns:
            (merged_records, merge_log)
        """
        self._merge_log = []
        working = list(records)

        layers = [
            self._layer1_doi,
            self._layer2_title_high,
            self._layer3_title_low,
            self._layer4_cross_language,
        ]
        for i, layer_fn in enumerate(layers):
            working = layer_fn(working)
            if progress_callback:
                progress_callback(i + 1, len(layers))

        return working, self._merge_log

    def _layer1_doi(self, records: list[Record]) -> list[Record]:
        """DOI exact match — auto-merge."""
        doi_map: dict[str, list[int]] = {}
        for i, r in enumerate(records):
            if r.doi:
                doi = r.doi.strip().lower()
                if doi:
                    doi_map.setdefault(doi, []).append(i)

        merged_indices: set[int] = set()

        for doi, indices in doi_map.items():
            if len(indices) < 2:
                continue
            primary_idx = indices[0]
            for dup_idx in indices[1:]:
                self._merge_log.append({
                    "layer": 1,
                    "type": "doi_exact",
                    "kept": records[primary_idx].title,
                    "merged": records[dup_idx].title,
                    "doi": doi,
                })
                records[primary_idx] = _merge_records(
                    records[primary_idx], records[dup_idx]
                )
                merged_indices.add(dup_idx)

        return [r for i, r in enumerate(records) if i not in merged_indices]

    def _layer2_title_high(self, records: list[Record]) -> list[Record]:
        """Title fuzzy match (>= 85%) + same year → auto-merge.

        Records are bucketed by year so comparisons are O(buckets × bucket²)
        instead of O(n²) — a huge win for large datasets spanning many years.
        """
        merged_indices: set[int] = set()

        # Bucket records by year
        year_buckets: dict[int, list[int]] = {}
        for i, r in enumerate(records):
            year_buckets.setdefault(r.year or 0, []).append(i)

        for indices in year_buckets.values():
            m = len(indices)
            for a in range(m):
                i = indices[a]
                if i in merged_indices:
                    continue
                for b in range(a + 1, m):
                    j = indices[b]
                    if j in merged_indices:
                        continue
                    r1, r2 = records[i], records[j]

                    sim = _title_similarity(r1.title, r2.title)
                    if sim >= self.title_threshold_high:
                        self._merge_log.append({
                            "layer": 2,
                            "type": "title_fuzzy_high",
                            "kept": r1.title,
                            "merged": r2.title,
                            "similarity": round(sim, 3),
                        })
                        records[i] = _merge_records(r1, r2)
                        merged_indices.add(j)

        return [r for i, r in enumerate(records) if i not in merged_indices]

    def _layer3_title_low(self, records: list[Record]) -> list[Record]:
        """Title fuzzy match (>= 70%) + same first author + same year → auto-merge.

        (PRD says "需人工确认" but in MVP we auto-merge and log for review.)

        Bucketed by (year, first-author) for O(buckets × bucket²) performance.
        """
        merged_indices: set[int] = set()

        # Bucket by (year, first_author_lower)
        from collections import defaultdict
        buckets: dict[tuple[int, str], list[int]] = defaultdict(list)
        for i, r in enumerate(records):
            fa = r.first_author
            if not fa:
                continue
            key = (r.year or 0, fa.full_name.lower())
            buckets[key].append(i)

        for indices in buckets.values():
            m = len(indices)
            for a in range(m):
                i = indices[a]
                if i in merged_indices:
                    continue
                for b in range(a + 1, m):
                    j = indices[b]
                    if j in merged_indices:
                        continue
                    r1, r2 = records[i], records[j]

                    sim = _title_similarity(r1.title, r2.title)
                    if sim >= self.title_threshold_low:
                        fa = r1.first_author
                        self._merge_log.append({
                            "layer": 3,
                            "type": "title_fuzzy_low",
                            "kept": r1.title,
                            "merged": r2.title,
                            "similarity": round(sim, 3),
                            "first_author": fa.full_name if fa else "",
                        })
                        records[i] = _merge_records(r1, r2)
                        merged_indices.add(j)

        return [r for i, r in enumerate(records) if i not in merged_indices]

    def _layer4_cross_language(self, records: list[Record]) -> list[Record]:
        """Cross-language dedup (CN ↔ EN).

        For CNKI (Chinese titles) vs WoS (English titles):
        - Priority: DOI match (already handled in layer 1)
        - Fallback: same first author + same year + same journal + same volume/pages
        """
        # Layer 1 already handles DOI matching across databases.
        # This layer adds author+year+journal+pages matching.
        merged_indices: set[int] = set()
        n = len(records)

        for i in range(n):
            if i in merged_indices:
                continue
            for j in range(i + 1, n):
                if j in merged_indices:
                    continue
                r1, r2 = records[i], records[j]

                # Only cross-source
                if r1.source_database == r2.source_database:
                    continue

                # Year must match
                if r1.year is None or r2.year is None or r1.year != r2.year:
                    continue

                # First author surname match
                fa1 = r1.first_author
                fa2 = r2.first_author
                if not fa1 or not fa2:
                    continue

                # Check surname or full name match
                s1 = (fa1.surname or fa1.full_name).lower()
                s2 = (fa2.surname or fa2.full_name).lower()
                if s1 != s2:
                    continue

                # Journal match (fuzzy)
                j1 = (r1.journal or "").lower()
                j2 = (r2.journal or "").lower()
                journal_sim = SequenceMatcher(None, j1, j2).ratio() if j1 and j2 else 0

                # Pages match
                pages_match = bool(
                    r1.pages
                    and r2.pages
                    and r1.pages.strip() == r2.pages.strip()
                )

                # Volume match
                vol_match = bool(
                    r1.volume
                    and r2.volume
                    and r1.volume.strip() == r2.volume.strip()
                )

                # Require at least 2 of 3 (journal, pages, volume) to match
                evidence = sum([journal_sim >= 0.8, pages_match, vol_match])
                if evidence >= 2:
                    self._merge_log.append({
                        "layer": 4,
                        "type": "cross_language",
                        "kept": r1.title,
                        "merged": r2.title,
                        "db1": r1.source_database,
                        "db2": r2.source_database,
                    })
                    records[i] = _merge_records(r1, r2)
                    merged_indices.add(j)

        return [r for i, r in enumerate(records) if i not in merged_indices]
