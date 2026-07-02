"""Plugable parser system for bibliographic data sources."""

from citationer.parsers.base import BaseParser
from citationer.parsers.cnki import CnkiExcelParser
from citationer.parsers.wos import WosExcelParser, WosTabDelimitedParser, WosTextParser

__all__ = [
    "BaseParser",
    "CnkiExcelParser",
    "WosExcelParser",
    "WosTabDelimitedParser",
    "WosTextParser",
]
