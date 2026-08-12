"""EndNote XML export parser."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from citationer.models.record import Author, Record
from citationer.parsers.base import BaseParser


class EndNoteXMLParser(BaseParser):
    """Parser for EndNote XML (.xml/.enl) exports."""

    @property
    def source_name(self) -> str:
        return "EndNote"

    def detect(self, filepath: Path) -> bool:
        if filepath.suffix.lower() not in {".xml", ".enl"}:
            return False
        try:
            with open(filepath, "rb") as f:
                header = f.read(200)
            return b"<?xml" in header or b"<records>" in header.lower()
        except Exception:  # noqa: BLE001
            return False

    def parse(self, filepath: Path) -> list[Record]:
        tree = ET.parse(filepath)
        root = tree.getroot()
        records: list[Record] = []
        for record in root.findall(".//record"):
            title = self._text(record, ".//title") or ""
            year_str = self._text(record, ".//year")
            year = int(year_str) if year_str and year_str.isdigit() else None
            authors = [
                Author(full_name=name.strip(), order=i + 1)
                for i, name in enumerate(self._texts(record, ".//author"))
                if name.strip()
            ]
            records.append(
                Record(
                    title=title,
                    year=year,
                    authors=authors,
                    journal=self._text(record, ".//secondary-title"),
                    doi=self._text(record, ".//accession-num"),
                    source_database="EndNote",
                )
            )
        return records

    def _text(self, element, path: str) -> str | None:
        found = element.find(path)
        if found is not None and found.text:
            return found.text.strip()
        return None

    def _texts(self, element, path: str) -> list[str]:
        return [e.text.strip() for e in element.findall(path) if e.text]
