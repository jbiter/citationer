"""Plugable parser system for bibliographic data sources."""

from citationer.parsers.base import BaseParser
from citationer.parsers.cnki import CnkiExcelParser
from citationer.parsers.cssci import CssciParser
from citationer.parsers.pubmed import PubMedParser
from citationer.parsers.scopus import ScopusParser
from citationer.parsers.wos import WosExcelParser, WosTabDelimitedParser, WosTextParser

__all__ = [
    "BaseParser",
    "CnkiExcelParser",
    "CssciParser",
    "PubMedParser",
    "ScopusParser",
    "WosExcelParser",
    "WosTabDelimitedParser",
    "WosTextParser",
]
