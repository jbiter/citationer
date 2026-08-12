"""Abstract base class for bibliographic parsers."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from importlib.metadata import entry_points
from pathlib import Path

from citationer.models.record import Record

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Abstract base parser that all data-source parsers implement.

    Usage::

        class MyParser(BaseParser):
            @property
            def source_name(self) -> str:
                return "MySource"

            def detect(self, filepath: Path) -> bool:
                return filepath.suffix == ".myfmt"

            def parse(self, filepath: Path) -> list[Record]:
                records = []
                # ... parse logic ...
                return records
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable source database name (e.g. 'CNKI', 'WoS')."""
        ...

    @abstractmethod
    def detect(self, filepath: Path) -> bool:
        """Return True if this parser can handle the given file.

        Detection is based on file extension, header content,
        internal structure, or a combination.
        """
        ...

    @abstractmethod
    def parse(self, filepath: Path) -> list[Record]:
        """Parse the file and return a list of unified Records."""
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(source={self.source_name!r})>"


class ParserRegistry:
    """Registry of all available parsers.

    Parsers are tried in order of registration; the first parser
    whose `detect()` returns True wins.
    """

    def __init__(self) -> None:
        self._parsers: list[BaseParser] = []

    def register(self, parser: BaseParser) -> None:
        """Register a parser instance."""
        self._parsers.append(parser)

    def find_parser(self, filepath: Path) -> BaseParser | None:
        """Find the first parser that can handle the file.

        Returns None if no parser matches.
        """
        for parser in self._parsers:
            if parser.detect(filepath):
                return parser
        return None

    def detect_format(self, filepath: Path) -> str | None:
        """Detect the source format name for a file.

        Returns the source_name string, or None if unrecognized.
        """
        parser = self.find_parser(filepath)
        return parser.source_name if parser else None

    @property
    def registered_sources(self) -> list[str]:
        """List of registered source names."""
        return [p.source_name for p in self._parsers]

    def __len__(self) -> int:
        return len(self._parsers)

    def __iter__(self):
        return iter(self._parsers)

    def register_from_entry_points(self) -> None:
        """Discover and register third-party parsers via entry points."""
        try:
            eps = entry_points(group="citationer.parsers")
        except Exception:  # pragma: no cover
            logger.debug("Unable to scan citationer.parsers entry points")
            return

        for ep in eps:
            try:
                factory = ep.load()
                if isinstance(factory, type) and issubclass(factory, BaseParser):
                    parser: BaseParser = factory()
                elif callable(factory):
                    parser = factory()
                    if not isinstance(parser, BaseParser):
                        raise TypeError(
                            f"Plugin {ep.name!r} factory did not return a BaseParser"
                        )
                else:
                    raise TypeError(
                        f"Plugin {ep.name!r} entry point is not a BaseParser subclass or factory"
                    )
                self.register(parser)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to load parser plugin %s: %s", ep.name, exc)
