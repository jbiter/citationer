"""PubMed MEDLINE / XML export parser."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree

from citationer.models.record import Author, DocType, Record
from citationer.parsers.base import BaseParser


class PubMedParser(BaseParser):
    """Parser for PubMed MEDLINE (XML) and NBIB export files."""

    @property
    def source_name(self) -> str:
        return "PubMed"

    def detect(self, filepath: Path) -> bool:
        suffix = filepath.suffix.lower()
        if suffix not in (".xml", ".nbib", ".txt"):
            return False

        try:
            with open(filepath, encoding="utf-8-sig", errors="ignore") as f:
                head = f.read(2000)
            # MEDLINE: starts with PMID or has <PubmedArticle> tags
            if "<PubmedArticle" in head or "<MedlineCitation" in head:
                return True
            if "PMID-" in head[:200]:
                return True
        except Exception:
            return False
        return False

    def parse(self, filepath: Path) -> list[Record]:
        try:
            return self._parse_xml(filepath)
        except Exception:
            pass
        return self._parse_medline(filepath)

    # ------------------------------------------------------------------
    # XML parsing (PubMed XML export)
    # ------------------------------------------------------------------

    def _parse_xml(self, filepath: Path) -> list[Record]:
        tree = ElementTree.parse(filepath)
        root = tree.getroot()
        records: list[Record] = []

        for article in root.iter("PubmedArticle"):
            try:
                records.append(self._xml_to_record(article, filepath.name))
            except Exception:
                continue

        return records

    def _xml_to_record(self, article, source_file: str) -> Record:
        citation = article.find(".//MedlineCitation")
        if citation is None:
            citation = article

        article_el = citation.find(".//Article")
        if article_el is None:
            return Record(title="", source_database="PubMed", source_file=source_file)

        # Title
        title_el = article_el.find(".//ArticleTitle")
        title = (title_el.text or "").strip() if title_el is not None else ""

        # Authors
        authors: list[Author] = []
        author_list = article_el.find(".//AuthorList")
        if author_list is not None:
            for i, au in enumerate(author_list.findall("Author")):
                ln = au.findtext("LastName") or ""
                fn = au.findtext("ForeName") or ""
                full = f"{ln}, {fn}" if ln and fn else (ln or fn)
                if full:
                    authors.append(Author(
                        full_name=full, surname=ln,
                        given_name=fn, order=i + 1,
                    ))

        # Year
        year: int | None = None
        pub_date = (
            citation.find(".//ArticleDate")
            or citation.find(".//PubDate")
            or citation.find(".//DateCompleted")
            or citation.find(".//DateRevised")
        )
        if pub_date is not None:
            y = pub_date.findtext("Year")
            if y:
                try:
                    year = int(y)
                except ValueError:
                    pass

        # Journal
        journal_el = article_el.find(".//Journal")
        journal: str | None = None
        volume: str | None = None
        issue: str | None = None
        pages: str | None = None
        issn: str | None = None

        if journal_el is not None:
            journal = (journal_el.findtext("Title") or "").strip() or None
            issn_el = journal_el.find(".//ISSN")
            if issn_el is not None:
                issn = (issn_el.text or "").strip() or None
            vol_el = journal_el.find(".//Volume")
            if vol_el is not None:
                volume = (vol_el.text or "").strip() or None
            iss_el = journal_el.find(".//Issue")
            if iss_el is not None:
                issue = (iss_el.text or "").strip() or None

        # Abstract
        abstract: str | None = None
        abs_el = article_el.find(".//Abstract")
        if abs_el is not None:
            parts = [t.text or "" for t in abs_el.findall("AbstractText")]
            abstract = " ".join(p.strip() for p in parts if p.strip()) or None

        # DOI
        doi: str | None = None
        for eid in article_el.findall(".//ELocationID"):
            if eid.get("EIdType") == "doi":
                doi = (eid.text or "").strip() or None

        # PMID
        pmid_el = citation.find(".//PMID")
        pmid = (pmid_el.text or "").strip() if pmid_el is not None else ""
        if not doi and pmid:
            doi = f"pmid:{pmid}"

        # Keywords
        keywords: list[str] = []
        kw_list = citation.find(".//KeywordList")
        if kw_list is not None:
            for kw in kw_list.findall("Keyword"):
                t = (kw.text or "").strip()
                if t:
                    keywords.append(t)

        # Language
        language: str | None = None
        lang_el = article_el.find(".//Language")
        if lang_el is not None:
            language = (lang_el.text or "").strip()[:3].lower() or None

        # Doc type
        pub_type_list = article_el.find(".//PublicationTypeList")
        doc_type = DocType.ARTICLE
        if pub_type_list is not None:
            for pt in pub_type_list.findall("PublicationType"):
                t = (pt.text or "").lower()
                if "review" in t:
                    doc_type = DocType.REVIEW
                    break

        return Record(
            title=title,
            title_en=title,
            authors=authors,
            year=year,
            journal=journal,
            volume=volume,
            issue=issue,
            pages=pages,
            doi=doi,
            issn=issn,
            abstract=abstract,
            keywords=keywords,
            language=language or "en",
            doc_type=doc_type,
            source_database="PubMed",
            source_file=source_file,
        )

    # ------------------------------------------------------------------
    # MEDLINE text parsing
    # ------------------------------------------------------------------

    def _parse_medline(self, filepath: Path) -> list[Record]:
        records: list[Record] = []
        current: dict[str, str] = {}
        current_tag = ""

        with open(filepath, encoding="utf-8-sig", errors="ignore") as f:
            for line in f:
                line = line.rstrip("\n\r")
                if not line.strip():
                    if current:
                        records.append(self._medline_to_record(current, filepath.name))
                        current = {}
                    continue

                m = re.match(r"^([A-Z]{2,4})\s{0,3}[- ]\s*(.*)", line)
                if m:
                    tag = m.group(1).strip()
                    value = m.group(2).strip()
                    if tag in current:
                        current[tag] += "; " + value
                    else:
                        current[tag] = value
                    current_tag = tag
                elif current_tag and line.startswith("      "):
                    current[current_tag] += " " + line.strip()

        if current:
            records.append(self._medline_to_record(current, filepath.name))

        return records

    def _medline_to_record(self, fields: dict[str, str], source_file: str) -> Record:
        def get(tag: str, default: str = "") -> str:
            return fields.get(tag, default)

        title = get("TI")
        authors: list[Author] = []
        au_field = get("AU")
        if au_field:
            for i, name in enumerate(au_field.split(";")):
                name = name.strip()
                if name:
                    authors.append(Author(full_name=name, order=i + 1))

        year: int | None = None
        dp = get("DP")
        m = re.search(r"(\d{4})", dp)
        if m:
            try:
                year = int(m.group(1))
            except ValueError:
                pass

        journal = get("TA") or get("SO") or get("JT") or None
        volume = get("VI") or None
        issue = get("IP") or None
        pages = get("PG") or None
        doi = get("AID") or get("LID") or None
        abstract = get("AB") or None
        language = get("LA") or None
        pmid = get("PMID") or ""

        keywords: list[str] = []
        ot = get("OT")
        if ot:
            keywords = [k.strip() for k in ot.split(";") if k.strip()]

        doc_type_str = get("PT", "").lower()
        doc_type = DocType.REVIEW if "review" in doc_type_str else DocType.ARTICLE

        return Record(
            title=title,
            title_en=title,
            authors=authors,
            year=year,
            journal=journal,
            volume=volume,
            issue=issue,
            pages=pages,
            doi=doi or (f"pmid:{pmid}" if pmid else None),
            abstract=abstract,
            keywords=keywords,
            language=language or "en",
            doc_type=doc_type,
            source_database="PubMed",
            source_file=source_file,
        )
