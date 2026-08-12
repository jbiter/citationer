"""Tests for parser plugin discovery."""

from pathlib import Path

from citationer.models.record import Record
from citationer.parsers.base import BaseParser, ParserRegistry


class FakeParser(BaseParser):
    @property
    def source_name(self) -> str:
        return "FakePlugin"

    def detect(self, filepath: Path) -> bool:
        return filepath.suffix == ".fake"

    def parse(self, filepath: Path) -> list[Record]:
        return []


def make_entry_point(name: str, factory):
    class _EP:
        def __init__(self, name, factory):
            self.name = name
            self._factory = factory

        def load(self):
            return self._factory

    return _EP(name, factory)


def test_registry_loads_entry_point_plugins(monkeypatch):
    registry = ParserRegistry()

    def _fake_eps(*, group):
        if group == "citationer.parsers":
            return [make_entry_point("fake", FakeParser)]
        return []

    monkeypatch.setattr(
        "citationer.parsers.base.entry_points", _fake_eps
    )
    registry.register_from_entry_points()

    assert len(registry) == 1
    assert registry.registered_sources == ["FakePlugin"]
