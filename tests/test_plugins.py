"""Tests for parser plugin discovery."""

from pathlib import Path

import pytest

from citationer.models.record import Record
from citationer.parsers.base import BaseParser, ParserRegistry


@pytest.fixture
def registry():
    """Return a fresh ParserRegistry instance."""
    return ParserRegistry()


class FakeParser(BaseParser):
    @property
    def source_name(self) -> str:
        return "FakePlugin"

    def detect(self, filepath: Path) -> bool:
        return filepath.suffix == ".fake"

    def parse(self, filepath: Path) -> list[Record]:
        return []


def make_entry_point(name: str, factory) -> object:
    class _EP:
        def __init__(self, name, factory):
            self.name = name
            self._factory = factory

        def load(self):
            return self._factory

    return _EP(name, factory)


def test_registry_loads_entry_point_plugins(registry, monkeypatch):
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


def test_registry_skips_entry_point_when_load_raises(registry, monkeypatch, caplog):
    class _BrokenEP:
        name = "broken"

        def load(self):
            raise RuntimeError("boom")

    def _fake_eps(*, group):
        if group == "citationer.parsers":
            return [_BrokenEP()]
        return []

    monkeypatch.setattr("citationer.parsers.base.entry_points", _fake_eps)

    with caplog.at_level("WARNING", logger="citationer.parsers.base"):
        registry.register_from_entry_points()

    assert len(registry) == 0
    assert any(
        "Failed to load parser plugin broken" in rec.message
        for rec in caplog.records
    )


def test_registry_skips_entry_point_when_factory_returns_non_parser(
    registry, monkeypatch, caplog
):
    def _fake_eps(*, group):
        if group == "citationer.parsers":
            return [make_entry_point("bad", lambda: "not a parser")]
        return []

    monkeypatch.setattr("citationer.parsers.base.entry_points", _fake_eps)

    with caplog.at_level("WARNING", logger="citationer.parsers.base"):
        registry.register_from_entry_points()

    assert len(registry) == 0
    assert any(
        "Failed to load parser plugin bad" in rec.message
        for rec in caplog.records
    )


def test_registry_handles_entry_points_scan_failure(registry, monkeypatch, caplog):
    def _fake_eps(*, group):
        raise RuntimeError("entry_points unavailable")

    monkeypatch.setattr("citationer.parsers.base.entry_points", _fake_eps)

    with caplog.at_level("DEBUG", logger="citationer.parsers.base"):
        registry.register_from_entry_points()

    assert len(registry) == 0
    assert any(
        "Unable to scan citationer.parsers entry points" in rec.message
        for rec in caplog.records
    )


def test_registry_preserves_existing_parsers_on_entry_points_failure(registry, monkeypatch):
    registry.register(FakeParser())

    def _fake_eps(*, group):
        raise RuntimeError("entry_points unavailable")

    monkeypatch.setattr("citationer.parsers.base.entry_points", _fake_eps)
    registry.register_from_entry_points()

    assert len(registry) == 1
    assert registry.registered_sources == ["FakePlugin"]


def test_get_registry_includes_entry_point_plugins(monkeypatch):
    from citationer.cli.scan_cmd import get_registry

    # Clear module-level cache so get_registry builds a fresh registry.
    monkeypatch.setattr("citationer.cli.scan_cmd._registry", None)

    def _fake_eps(*, group):
        if group == "citationer.parsers":
            return [make_entry_point("fake", FakeParser)]
        return []

    monkeypatch.setattr("citationer.parsers.base.entry_points", _fake_eps)

    registry = get_registry()
    assert "FakePlugin" in registry.registered_sources
    # Built-in parsers are still registered.
    assert "CNKI" in registry.registered_sources


def test_endnote_example_plugin_loads(tmp_path, monkeypatch):
    """If endnote-plugin is installed, it should appear in the registry."""
    from citationer.parsers.base import entry_points

    # 检查是否真的安装了该 entry point
    try:
        eps = list(entry_points(group="citationer.parsers"))
    except Exception:  # noqa: BLE001
        pytest.skip("No entry points available")

    names = [ep.name for ep in eps]
    if "endnote" not in names:
        pytest.skip("endnote-plugin not installed")

    from citationer.cli.scan_cmd import get_registry

    monkeypatch.setattr("citationer.cli.scan_cmd._registry", None)
    registry = get_registry()
    assert "EndNote" in registry.registered_sources


def test_plugins_list_command(cli_runner):
    from citationer.cli.main import app

    result = cli_runner.invoke(app, ["plugins", "list"])
    assert result.exit_code == 0
    assert "CNKI" in result.output
    assert "built-in" in result.output


def test_plugins_list_command_handles_broken_entry_point(
    cli_runner, monkeypatch, caplog
):
    class _BrokenEP:
        name = "broken"

        def load(self):
            raise RuntimeError("boom")

    def _fake_eps(*, group):
        if group == "citationer.parsers":
            return [_BrokenEP()]
        return []

    monkeypatch.setattr("citationer.parsers.base.entry_points", _fake_eps)

    from citationer.cli.main import app

    with caplog.at_level("WARNING", logger="citationer.cli.plugins_cmd"):
        result = cli_runner.invoke(app, ["plugins", "list"])

    assert result.exit_code == 0
    assert "CNKI" in result.output
    assert any(
        "Could not inspect plugin broken" in rec.message
        for rec in caplog.records
    )


def test_plugins_list_command_handles_entry_points_enumeration_failure(
    cli_runner, monkeypatch, caplog
):
    def _fake_eps(*, group):
        raise RuntimeError("entry_points unavailable")

    monkeypatch.setattr("citationer.parsers.base.entry_points", _fake_eps)

    from citationer.cli.main import app

    with caplog.at_level("WARNING", logger="citationer.cli.plugins_cmd"):
        result = cli_runner.invoke(app, ["plugins", "list"])

    assert result.exit_code == 0
    assert "CNKI" in result.output
    assert any(
        "Unable to enumerate citationer.parsers entry points" in rec.message
        for rec in caplog.records
    )
