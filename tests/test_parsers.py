"""Tests for bibliographic parsers."""

from pathlib import Path

from citationer.parsers.base import ParserRegistry
from citationer.parsers.bibtex import BibTeXParser
from citationer.parsers.cnki import CnkiExcelParser
from citationer.parsers.wos import WosExcelParser, WosTextParser


class TestParserRegistry:
    def test_register_and_find(self):
        registry = ParserRegistry()
        registry.register(CnkiExcelParser())
        registry.register(WosTextParser())

        # Should find parser for .xlsx
        # (won't actually detect since file doesn't exist, but parser is registered)
        assert len(registry) == 2
        assert "CNKI" in registry.registered_sources
        assert "WoS" in registry.registered_sources

    def test_find_parser_none(self, tmp_path: Path):
        registry = ParserRegistry()
        registry.register(CnkiExcelParser())

        f = tmp_path / "test.xyz"
        f.write_text("unknown format")
        assert registry.find_parser(f) is None


class TestCnkiExcelParser:
    def test_detect_not_excel(self, tmp_path: Path):
        parser = CnkiExcelParser()
        f = tmp_path / "test.txt"
        f.write_text("some text")
        assert not parser.detect(f)

    def test_source_name(self):
        parser = CnkiExcelParser()
        assert parser.source_name == "CNKI"


class TestWosTextParser:
    def test_detect_wos_format(self, tmp_path: Path):
        parser = WosTextParser()
        f = tmp_path / "test.txt"
        f.write_text("PT J\nAU Smith, John\nTI Test Paper\nER\n")
        assert parser.detect(f)

    def test_detect_not_wos(self, tmp_path: Path):
        parser = WosTextParser()
        f = tmp_path / "test.txt"
        f.write_text("This is a plain text file\nNot a WoS export\n")
        assert not parser.detect(f)

    def test_detect_ciw_extension(self, tmp_path: Path):
        parser = WosTextParser()
        f = tmp_path / "wos_search.ciw"
        f.write_text("PT J\nER\n")
        assert parser.detect(f)

    def test_parse_single_record(self, tmp_path: Path):
        parser = WosTextParser()
        content = """FN Clarivate Analytics Web of Science
PT J
AU Smith, John; Jones, Mary
TI A Study of Machine Learning in Bibliometrics
SO Journal of Informetrics
PY 2024
VL 18
IS 2
BP 123
EP 145
DI 10.1000/example
AB This is a test abstract.
DE machine learning; bibliometrics
TC 5
DT Article
LA English
ER
EF"""
        f = tmp_path / "test.txt"
        f.write_text(content)

        records = parser.parse(f)
        assert len(records) == 1
        r = records[0]
        assert r.title == "A Study of Machine Learning in Bibliometrics"
        assert r.year == 2024
        assert r.journal == "Journal of Informetrics"
        assert r.doi == "10.1000/example"
        assert r.citation_count == 5
        assert len(r.authors) == 2
        assert r.authors[0].full_name == "Smith, John"
        assert "machine learning" in r.keywords
        assert "bibliometrics" in r.keywords

    def test_source_name(self):
        parser = WosTextParser()
        assert parser.source_name == "WoS"


class TestBibTeXParser:
    def test_parse_nested_braces(self, tmp_path: Path):
        parser = BibTeXParser()
        content = r"""@article{key1,
  title = {Role of {BRCA1} in DNA repair},
  author = {Smith, John},
  year = {2024},
  journal = {Nature},
}
"""
        f = tmp_path / "test.bib"
        f.write_text(content, encoding="utf-8")

        records = parser.parse(f)
        assert len(records) == 1
        assert records[0].title == "Role of {BRCA1} in DNA repair"

    def test_parse_simple_bibtex(self, tmp_path: Path):
        parser = BibTeXParser()
        content = """@article{key1,
  title = {Simple Title},
  author = {Doe, Jane and Smith, John},
  year = {2023},
  journal = {Science},
}
"""
        f = tmp_path / "test.bib"
        f.write_text(content, encoding="utf-8")

        records = parser.parse(f)
        assert len(records) == 1
        r = records[0]
        assert r.title == "Simple Title"
        assert r.year == 2023
        assert len(r.authors) == 2


class TestWosExcelParser:
    def test_detect_not_excel(self, tmp_path: Path):
        parser = WosExcelParser()
        f = tmp_path / "test.txt"
        f.write_text("not excel")
        assert not parser.detect(f)

    def test_source_name(self):
        parser = WosExcelParser()
        assert parser.source_name == "WoS"
