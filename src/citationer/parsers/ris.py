"""RIS (Research Information Systems) export parser."""

from __future__ import annotations

import re
from pathlib import Path

from citationer.models.record import Author, DocType, Record
from citationer.parsers.base import BaseParser


class RISParser(BaseParser):
    """Parser for RIS (.ris) and NBIB files.

    RIS uses two-character tags: ``TI - Title``, ``AU - Author``,
    ``PY - Year``, ``ER - End of Record``, etc.
    """

    @property
    def source_name(self) -> str:
        return "RIS"

    def detect(self, filepath: Path) -> bool:
        suffix = filepath.suffix.lower()
        if suffix not in (".ris", ".txt"):
            return False

        try:
            with open(filepath, encoding="utf-8-sig", errors="ignore") as f:
                head = f.read(4000)
            # RIS has TY - at the start of entries and ER - as terminator
            if re.search(r"^TY  -", head, re.MULTILINE):
                return True
        except Exception:
            return False
        return False

    def parse(self, filepath: Path) -> list[Record]:
        records: list[Record] = []
        current: dict[str, list[str]] = {}

        with open(filepath, encoding="utf-8-sig", errors="ignore") as f:
            for line in f:
                line = line.rstrip("\n\r")

                # End of record: "ER  -" (RIS terminator)
                if line.startswith("ER"):
                    if current:
                        rec = self._to_record(current, filepath.name)
                        if rec:
                            records.append(rec)
                        current = {}
                    continue

                # Start of a new record (some exporters omit ER terminators)
                if line.startswith("TY  -"):
                    if current:
                        rec = self._to_record(current, filepath.name)
                        if rec:
                            records.append(rec)
                        current = {}

                # Tag line: "XX  - value"
                m = re.match(r"^([A-Z][A-Z0-9]) ? ?- (.*)$", line)
                if m:
                    tag = m.group(1)
                    value = m.group(2).strip()
                    current.setdefault(tag, []).append(value)
                    continue

                # Continuation line (starts with whitespace)
                if current and line and line[0] in (" ", "\t"):
                    last_tag = list(current.keys())[-1] if current else None
                    if last_tag and current[last_tag]:
                        current[last_tag][-1] += " " + line.strip()

        # Handle trailing record
        if current:
            rec = self._to_record(current, filepath.name)
            if rec:
                records.append(rec)

        return records

    def _to_record(
        self, fields: dict[str, list[str]], source_file: str
    ) -> Record | None:
        def get(tag: str) -> str:
            """Get first value for a tag."""
            vals = fields.get(tag, [])
            return vals[0].strip() if vals else ""

        def get_all(tag: str) -> list[str]:
            """Get all values for a tag."""
            return [v.strip() for v in fields.get(tag, []) if v.strip()]

        title = get("TI") or get("T1")
        if not title:
            return None

        # Authors
        au_names = get_all("AU") or get_all("A1")
        authors = [
            Author(full_name=n, order=i + 1) for i, n in enumerate(au_names)
        ]

        # Year
        year: int | None = None
        y = get("PY") or get("Y1")
        if y:
            m = re.search(r"(\d{4})", y)
            if m:
                try:
                    year = int(m.group(1))
                except ValueError:
                    pass

        # Journal
        journal = get("JO") or get("JA") or get("JF") or get("JT") or None

        # Volume, Issue, Pages
        volume = get("VL") or None
        issue = get("IS") or None
        sp = get("SP")
        ep = get("EP")
        pages = f"{sp}-{ep}" if sp and ep else (sp or get("PG") or None)

        # DOI
        doi = get("DO") or get("DI") or None

        # Keywords
        keywords = get_all("KW")

        # Abstract
        abstract = get("AB") or None

        # Language
        language = (get("LA") or "en").lower()[:3] or None

        # Doc type
        doc_type = self._map_type(get("TY"))

        # References
        refs = get_all("CR")
        references = refs if refs else None

        return Record(
            title=title,
            authors=authors,
            year=year,
            journal=journal,
            volume=volume,
            issue=issue,
            pages=pages,
            doi=doi,
            abstract=abstract,
            keywords=keywords,
            language=language or "en",
            doc_type=doc_type,
            references=references,
            source_database="RIS",
            source_file=source_file,
        )

    @staticmethod
    def _map_type(ty: str) -> DocType:
        ty = ty.upper()
        if ty in ("JOUR", "RPRT", "CTLG"):
            return DocType.ARTICLE
        if ty in ("BOOK"):
            return DocType.BOOK
        if ty in ("CHAP"):
            return DocType.BOOK_CHAPTER
        if ty in ("CONF", "CPAPER"):
            return DocType.CONFERENCE
        if ty in ("THES", "UNPB"):
            return DocType.THESIS
        if ty in ("REVIEW",):
            return DocType.REVIEW
        return DocType.OTHER
