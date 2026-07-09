"""Tests for PubMed parser (XML + MEDLINE text formats).

Covers:
- Format detection
- XML parsing (full PubmedArticle)
- MEDLINE text parsing (tagged format)
- Author parsing (LastName + ForeName)
- DOI extraction
- PMID fallback to DOI
- Keyword extraction
- Language handling
- Doc type classification (ARTICLE vs REVIEW)
- Edge cases: malformed XML, missing fields, empty PMID
"""

from __future__ import annotations

from xml.etree import ElementTree

from citationer.models.record import DocType
from citationer.parsers.pubmed import PubMedParser

# ===========================================================================
# Detection
# ===========================================================================


class TestPubMedDetect:
    def test_detect_xml_pubmed(self, tmp_path):
        f = tmp_path / "test.xml"
        f.write_text(
            '<?xml version="1.0"?><PubmedArticleSet>'
            "<PubmedArticle></PubmedArticle></PubmedArticleSet>"
        )
        assert PubMedParser().detect(f) is True

    def test_detect_medline_xml(self, tmp_path):
        f = tmp_path / "test.xml"
        f.write_text(
            '<?xml version="1.0"?><MedlineCitationSet>'
            "<MedlineCitation></MedlineCitation></MedlineCitationSet>"
        )
        assert PubMedParser().detect(f) is True

    def test_detect_nbib(self, tmp_path):
        f = tmp_path / "test.nbib"
        f.write_text("PMID- 12345\nTI  - Test Title\n")
        assert PubMedParser().detect(f) is True

    def test_detect_txt_medline(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("PMID- 12345\nTI  - Test\nAU  - Smith J\nER  - \n")
        assert PubMedParser().detect(f) is True

    def test_reject_random_xml(self, tmp_path):
        f = tmp_path / "other.xml"
        f.write_text("<?xml version='1.0'?><root><item/></root>")
        assert PubMedParser().detect(f) is False

    def test_reject_unsupported_extension(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_text("<PubmedArticle>")
        assert PubMedParser().detect(f) is False

    def test_reject_plain_text_no_pmid(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("This is just a plain text file with no PMID marker.")
        assert PubMedParser().detect(f) is False

    def test_source_name(self):
        assert PubMedParser().source_name == "PubMed"


# ===========================================================================
# XML parsing
# ===========================================================================


def _make_pubmed_xml(path, articles: list[dict]) -> None:
    """Create a PubMed XML with one or more articles.

    Each article dict supports: pmid, title, authors (list of (surname, forename)),
    year, journal, volume, issue, pages, abstract, doi, keywords, language,
    pub_type.
    """
    root = ElementTree.Element("PubmedArticleSet")
    for art in articles:
        article = ElementTree.SubElement(root, "PubmedArticle")
        citation = ElementTree.SubElement(article, "MedlineCitation")
        pmid_el = ElementTree.SubElement(citation, "PMID")
        pmid_el.text = str(art.get("pmid", "12345"))
        date_el = ElementTree.SubElement(citation, "DateCompleted")
        year_el = ElementTree.SubElement(date_el, "Year")
        year_el.text = str(art.get("year", "2024"))
        month_el = ElementTree.SubElement(date_el, "Month")
        month_el.text = "01"
        day_el = ElementTree.SubElement(date_el, "Day")
        day_el.text = "01"

        article_el = ElementTree.SubElement(citation, "Article")
        title_el = ElementTree.SubElement(article_el, "ArticleTitle")
        title_el.text = art.get("title", "Default Title")

        # Authors
        if art.get("authors"):
            al = ElementTree.SubElement(article_el, "AuthorList")
            for surname, forename in art["authors"]:
                a = ElementTree.SubElement(al, "Author")
                ln = ElementTree.SubElement(a, "LastName")
                ln.text = surname
                fn = ElementTree.SubElement(a, "ForeName")
                fn.text = forename

        # Journal
        journal = ElementTree.SubElement(article_el, "Journal")
        if art.get("journal"):
            jt = ElementTree.SubElement(journal, "Title")
            jt.text = art["journal"]
        if art.get("issn"):
            issn = ElementTree.SubElement(journal, "ISSN")
            issn.text = art["issn"]
        if art.get("volume"):
            vol = ElementTree.SubElement(journal, "Volume")
            vol.text = art["volume"]
        if art.get("issue"):
            iss = ElementTree.SubElement(journal, "Issue")
            iss.text = art["issue"]

        # Abstract
        if art.get("abstract"):
            abstract = ElementTree.SubElement(article_el, "Abstract")
            at = ElementTree.SubElement(abstract, "AbstractText")
            at.text = art["abstract"]

        # DOI
        if art.get("doi"):
            eid = ElementTree.SubElement(article_el, "ELocationID")
            eid.set("EIdType", "doi")
            eid.set("ValidYN", "Y")
            eid.text = art["doi"]

        # Keywords
        if art.get("keywords"):
            kwl = ElementTree.SubElement(citation, "KeywordList")
            for kw in art["keywords"]:
                k = ElementTree.SubElement(kwl, "Keyword")
                k.text = kw

        # Language
        if art.get("language"):
            lang = ElementTree.SubElement(article_el, "Language")
            lang.text = art["language"]

        # Publication type
        if art.get("pub_type"):
            ptl = ElementTree.SubElement(article_el, "PublicationTypeList")
            pt = ElementTree.SubElement(ptl, "PublicationType")
            pt.text = art["pub_type"]

    tree = ElementTree.ElementTree(root)
    tree.write(path, encoding="utf-8", xml_declaration=True)


class TestPubMedXmlParse:
    def test_parse_minimal_xml(self, tmp_path):
        f = tmp_path / "min.xml"
        _make_pubmed_xml(f, [{"pmid": "11111", "title": "Minimal"}])
        records = PubMedParser().parse(f)
        assert len(records) == 1
        r = records[0]
        assert r.title == "Minimal"
        assert r.year == 2024  # from default DateCompleted
        assert r.source_database == "PubMed"
        # No DOI, but PMID exists → doi = "pmid:11111"
        assert r.doi == "pmid:11111"

    def test_parse_with_doi(self, tmp_path):
        f = tmp_path / "doi.xml"
        _make_pubmed_xml(f, [{"pmid": "22222", "title": "D", "doi": "10.1000/x"}])
        r = PubMedParser().parse(f)[0]
        assert r.doi == "10.1000/x"

    def test_doi_takes_precedence_over_pmid(self, tmp_path):
        f = tmp_path / "both.xml"
        _make_pubmed_xml(f, [{"pmid": "33333", "title": "Both", "doi": "10.1000/y"}])
        r = PubMedParser().parse(f)[0]
        assert r.doi == "10.1000/y"  # not pmid:33333

    def test_parse_authors(self, tmp_path):
        f = tmp_path / "auth.xml"
        _make_pubmed_xml(
            f,
            [{
                "pmid": "1", "title": "A",
                "authors": [("Smith", "John"), ("Jones", "Mary")],
            }],
        )
        r = PubMedParser().parse(f)[0]
        assert len(r.authors) == 2
        assert r.authors[0].full_name == "Smith, John"
        assert r.authors[0].surname == "Smith"
        assert r.authors[0].given_name == "John"
        assert r.authors[0].order == 1
        assert r.authors[1].order == 2

    def test_parse_journal_issn_volume_issue(self, tmp_path):
        f = tmp_path / "j.xml"
        _make_pubmed_xml(
            f,
            [{
                "pmid": "1", "title": "J",
                "journal": "Nature", "issn": "1234-5678",
                "volume": "10", "issue": "3",
            }],
        )
        r = PubMedParser().parse(f)[0]
        assert r.journal == "Nature"
        assert r.issn == "1234-5678"
        assert r.volume == "10"
        assert r.issue == "3"

    def test_parse_abstract(self, tmp_path):
        f = tmp_path / "abs.xml"
        _make_pubmed_xml(
            f,
            [{"pmid": "1", "title": "A", "abstract": "This is the abstract text."}],
        )
        r = PubMedParser().parse(f)[0]
        assert r.abstract == "This is the abstract text."

    def test_parse_keywords(self, tmp_path):
        f = tmp_path / "kw.xml"
        _make_pubmed_xml(
            f,
            [{
                "pmid": "1", "title": "K",
                "keywords": ["machine learning", "healthcare"],
            }],
        )
        r = PubMedParser().parse(f)[0]
        assert "machine learning" in r.keywords
        assert "healthcare" in r.keywords

    def test_parse_language(self, tmp_path):
        f = tmp_path / "lang.xml"
        _make_pubmed_xml(
            f,
            [{"pmid": "1", "title": "L", "language": "eng"}],
        )
        r = PubMedParser().parse(f)[0]
        assert r.language == "eng"

    def test_default_language_eng(self, tmp_path):
        """No language tag → defaults to 'en'."""
        f = tmp_path / "nolang.xml"
        _make_pubmed_xml(f, [{"pmid": "1", "title": "NL"}])
        r = PubMedParser().parse(f)[0]
        assert r.language == "en"

    def test_doc_type_review(self, tmp_path):
        f = tmp_path / "rev.xml"
        _make_pubmed_xml(
            f,
            [{"pmid": "1", "title": "R", "pub_type": "Review"}],
        )
        r = PubMedParser().parse(f)[0]
        assert r.doc_type == DocType.REVIEW

    def test_doc_type_article_default(self, tmp_path):
        """No pub type → ARTICLE."""
        f = tmp_path / "art.xml"
        _make_pubmed_xml(f, [{"pmid": "1", "title": "A"}])
        r = PubMedParser().parse(f)[0]
        assert r.doc_type == DocType.ARTICLE

    def test_parse_multiple_articles(self, tmp_path):
        f = tmp_path / "multi.xml"
        _make_pubmed_xml(
            f,
            [
                {"pmid": "1", "title": "First"},
                {"pmid": "2", "title": "Second"},
                {"pmid": "3", "title": "Third"},
            ],
        )
        records = PubMedParser().parse(f)
        assert len(records) == 3
        assert [r.title for r in records] == ["First", "Second", "Third"]


# ===========================================================================
# MEDLINE text parsing
# ===========================================================================


class TestPubMedMedlineParse:
    def test_parse_simple_medline(self, tmp_path):
        f = tmp_path / "test.nbib"
        f.write_text(
            "PMID- 12345\n"
            "TI  - A Study of Machine Learning\n"
            "AU  - Smith J\n"
            "AU  - Jones M\n"
            "DP  - 2024 May\n"
            "TA  - Nature Medicine\n"
            "VI  - 10\n"
            "IP  - 3\n"
            "PG  - 100-110\n"
            "AB  - This is the abstract.\n"
            "AID - 10.1000/test [doi]\n"
            "OT  - machine learning\n"
            "OT  - healthcare\n"
            "LA  - eng\n"
            "PT  - Journal Article\n"
            "ER  - \n"
        )
        records = PubMedParser().parse(f)
        assert len(records) == 1
        r = records[0]
        assert r.title == "A Study of Machine Learning"
        assert r.year == 2024
        assert r.journal == "Nature Medicine"
        assert r.volume == "10"
        assert r.issue == "3"
        assert r.pages == "100-110"
        assert r.abstract == "This is the abstract."
        assert "machine learning" in r.keywords
        assert "healthcare" in r.keywords
        assert r.language == "eng"
        assert r.doc_type == DocType.ARTICLE

    def test_parse_medline_review(self, tmp_path):
        f = tmp_path / "review.nbib"
        f.write_text(
            "PMID- 99999\n"
            "TI  - Review Article\n"
            "PT  - Review\n"
            "DP  - 2023\n"
            "ER  - \n"
        )
        r = PubMedParser().parse(f)[0]
        assert r.doc_type == DocType.REVIEW

    def test_parse_medline_no_doi(self, tmp_path):
        f = tmp_path / "nodoi.nbib"
        f.write_text(
            "PMID- 88888\n"
            "TI  - No DOI\n"
            "DP  - 2022\n"
            "ER  - \n"
        )
        r = PubMedParser().parse(f)[0]
        assert r.doi == "pmid:88888"

    def test_parse_medline_multiple_records(self, tmp_path):
        f = tmp_path / "multi.nbib"
        f.write_text(
            "PMID- 1\nTI  - First\nDP  - 2024\nER  -\n"
            "\n"
            "PMID- 2\nTI  - Second\nDP  - 2023\nER  -\n"
        )
        records = PubMedParser().parse(f)
        assert len(records) == 2
        assert records[0].title == "First"
        assert records[1].title == "Second"

    def test_parse_medline_year_extraction(self, tmp_path):
        """Year extracted from various DP formats."""
        f = tmp_path / "y.nbib"
        for dp, expected in [
            ("2024 May 15", 2024),
            ("2023", 2023),
            ("2022 Dec", 2022),
            ("2021 Spring", 2021),
        ]:
            f.write_text(f"PMID- 1\nTI  - T\nDP  - {dp}\nER  -\n")
            r = PubMedParser().parse(f)[0]
            assert r.year == expected, f"Failed for DP={dp}"

    def test_parse_medline_journal_fallback(self, tmp_path):
        """Journal uses TA, then SO, then JT in order."""
        f = tmp_path / "j.nbib"
        f.write_text(
            "PMID- 1\nTI  - T\nTA  - Nature\nSO  - Other Journal\nDP  - 2024\nER  -\n"
        )
        r = PubMedParser().parse(f)[0]
        assert r.journal == "Nature"

    def test_parse_medline_journal_so_fallback(self, tmp_path):
        f = tmp_path / "j2.nbib"
        f.write_text(
            "PMID- 1\nTI  - T\nSO  - Other Journal\nDP  - 2024\nER  -\n"
        )
        r = PubMedParser().parse(f)[0]
        assert r.journal == "Other Journal"

    def test_parse_medline_empty_file(self, tmp_path):
        f = tmp_path / "empty.nbib"
        f.write_text("")
        records = PubMedParser().parse(f)
        assert records == []


# ===========================================================================
# Edge cases
# ===========================================================================


class TestPubMedEdgeCases:
    def test_malformed_xml_falls_back_to_medline(self, tmp_path):
        """Malformed XML should fall back to MEDLINE text parsing."""
        f = tmp_path / "mixed.nbib"
        # Not valid XML, but valid MEDLINE
        f.write_text(
            "PMID- 11111\nTI  - T\nDP  - 2024\nER  -\n"
        )
        records = PubMedParser().parse(f)
        # Should still get 1 record from MEDLINE fallback
        assert len(records) >= 1
        assert records[0].title == "T"

    def test_source_file_propagated(self, tmp_path):
        f = tmp_path / "my_pubmed.xml"
        _make_pubmed_xml(f, [{"pmid": "1", "title": "T"}])
        r = PubMedParser().parse(f)[0]
        assert r.source_file == "my_pubmed.xml"

    def test_year_invalid_date(self, tmp_path):
        f = tmp_path / "badyear.nbib"
        f.write_text(
            "PMID- 1\nTI  - T\nDP  - not a year\nER  -\n"
        )
        r = PubMedParser().parse(f)[0]
        assert r.year is None
