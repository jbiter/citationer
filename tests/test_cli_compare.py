"""CLI integration tests for `citationer compare`."""

from __future__ import annotations

import json

from citationer.cli.main import app
from citationer.models.record import Author, Institution, Record
from tests._helpers import seed_cli_db


def _setup_compare_data(clean_cwd):
    records = [
        Record(
            title="Shared Paper",
            year=2024,
            doi="10.1000/shared",
            source_database="CNKI",
            source_file="cnki.xlsx",
            authors=[Author(full_name="张伟", order=1)],
            keywords=["深度学习", "医疗"],
            institutions=[Institution(name="清华")],
        ),
        Record(
            title="Shared Paper Review",
            year=2024,
            doi="10.1000/shared",
            source_database="WoS",
            source_file="wos.txt",
            authors=[Author(full_name="Zhang, W.", order=1)],
            keywords=["deep learning", "healthcare"],
            institutions=[Institution(name="Tsinghua")],
        ),
        Record(
            title="CNKI Only",
            year=2023,
            source_database="CNKI",
            source_file="cnki.xlsx",
            authors=[Author(full_name="李强", order=1)],
            keywords=["机器学习"],
        ),
        Record(
            title="WoS Only",
            year=2022,
            source_database="WoS",
            source_file="wos.txt",
            authors=[Author(full_name="Smith, J.", order=1)],
            keywords=["neural networks"],
        ),
    ]
    seed_cli_db(clean_cwd, records)


class TestCompareOverview:
    def test_overview_table(self, cli_runner, clean_cwd, monkeypatch):
        _setup_compare_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["compare", "overview"])
        assert result.exit_code == 0, f"Output: {result.output}"
        assert "CNKI" in result.output
        assert "WoS" in result.output

    def test_overview_json(self, cli_runner, clean_cwd, monkeypatch):
        _setup_compare_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["compare", "overview", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "overviews" in data
        assert "overlaps" in data
        assert data["overlaps"][0]["doi_overlap"] == 1

    def test_overview_csv(self, cli_runner, clean_cwd, monkeypatch):
        _setup_compare_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        output = clean_cwd / "compare.csv"
        result = cli_runner.invoke(
            app, ["compare", "overview", "--format", "csv", "--output", str(output)]
        )
        assert result.exit_code == 0
        assert output.exists()
        text = output.read_text(encoding="utf-8")
        assert "CNKI" in text

    def test_overview_by_file(self, cli_runner, clean_cwd, monkeypatch):
        _setup_compare_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["compare", "overview", "--by", "file"])
        assert result.exit_code == 0
        assert "cnki.xlsx" in result.output


class TestCompareTrends:
    def test_trends_table(self, cli_runner, clean_cwd, monkeypatch):
        _setup_compare_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["compare", "trends"])
        assert result.exit_code == 0
        assert "2024" in result.output

    def test_trends_json(self, cli_runner, clean_cwd, monkeypatch):
        _setup_compare_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["compare", "trends", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "year_counts" in data
        assert "slopes" in data


class TestCompareTopics:
    def test_topics_table(self, cli_runner, clean_cwd, monkeypatch):
        _setup_compare_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["compare", "topics"])
        assert result.exit_code == 0

    def test_topics_csv(self, cli_runner, clean_cwd, monkeypatch):
        _setup_compare_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        output = clean_cwd / "topics.csv"
        result = cli_runner.invoke(
            app, ["compare", "topics", "--format", "csv", "--output", str(output)]
        )
        assert result.exit_code == 0
        assert output.exists()


class TestCompareNetwork:
    def test_network_table(self, cli_runner, clean_cwd, monkeypatch):
        _setup_compare_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["compare", "network", "--min-papers", "1"])
        assert result.exit_code == 0

    def test_network_institutions(self, cli_runner, clean_cwd, monkeypatch):
        _setup_compare_data(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["compare", "network", "--type", "institutions", "--min-papers", "1"]
        )
        assert result.exit_code == 0


class TestCompareEmpty:
    def test_compare_no_data(self, cli_runner, clean_cwd, monkeypatch):
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["compare", "overview"])
        assert result.exit_code == 0
        assert "没有记录" in result.output

    def test_compare_single_dataset(self, cli_runner, clean_cwd, monkeypatch):
        records = [
            Record(title="A", year=2024, source_database="DB1"),
        ]
        seed_cli_db(clean_cwd, records)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["compare", "overview"])
        assert result.exit_code == 0
        assert "至少" in result.output
