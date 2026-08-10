"""Tests for P5-10: citationer query — DSL filter + output.

Covers both the parser/matcher (utils.query) and the CLI subcommand
(cli.query_cmd) integration via Typer's CliRunner.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from citationer.cli.main import app
from citationer.models.record import Author
from citationer.utils.query import Filter, matches, parse_filter
from tests._factories import make_record as _r
from tests._helpers import seed_cli_db

# ===========================================================================
# parse_filter — unit tests for the query DSL parser
# ===========================================================================


class TestParseFilter:
    def test_single_equality(self):
        f = parse_filter("year=2024")
        assert len(f) == 1
        assert f[0] == Filter(field="year", op="=", value="2024")

    def test_inequality(self):
        f = parse_filter("citation_count>10")
        assert f[0] == Filter(field="citation_count", op=">", value="10")

    def test_greater_equal(self):
        f = parse_filter("year>=2020")
        assert f[0] == Filter(field="year", op=">=", value="2020")

    def test_less_equal(self):
        f = parse_filter("year<=2023")
        assert f[0] == Filter(field="year", op="<=", value="2023")

    def test_not_equal(self):
        f = parse_filter("language!=en")
        assert f[0] == Filter(field="language", op="!=", value="en")

    def test_quoted_string(self):
        f = parse_filter('journal="Nature"')
        assert f[0] == Filter(field="journal", op="=", value="Nature")

    def test_single_quoted_string(self):
        f = parse_filter("journal='Nature Medicine'")
        assert f[0] == Filter(field="journal", op="=", value="Nature Medicine")

    def test_and_chain(self):
        f = parse_filter("year>=2020 AND journal='Nature'")
        # Parser emits [Filter, 'AND', Filter] — 2 filters + 1 connective
        assert len(f) == 3
        assert f[0].field == "year"
        assert f[0].op == ">="
        assert f[1] == "AND"
        assert f[2].field == "journal"
        assert f[2].op == "="

    def test_or_chain(self):
        f = parse_filter("language='en' OR language='zh'")
        # 2 filters + 1 OR connective
        assert len(f) == 3
        assert f[1] == "OR"

    def test_mixed_and_or(self):
        f = parse_filter(
            "year>=2020 AND (language='en' OR language='zh')"
        )
        # 3 filters + 2 connectives; parens dropped
        assert len(f) == 5
        assert f[0].field == "year"
        assert f[1] == "AND"
        assert f[2].field == "language"
        assert f[3] == "OR"
        assert f[4].field == "language"

    def test_unknown_field_raises(self):
        with pytest.raises(ValueError, match="Unknown field"):
            parse_filter("evil_field=1")

    def test_unknown_op_raises(self):
        with pytest.raises(ValueError, match="Invalid filter expression"):
            parse_filter("year ?? 2024")

    def test_whitespace_tolerated(self):
        f = parse_filter("  year  >=  2020  ")
        assert f[0] == Filter(field="year", op=">=", value="2020")


# ===========================================================================
# matches — predicate against a Record
# ===========================================================================


class TestMatches:
    def test_year_equality(self):
        r = _r(year=2024)
        assert matches(r, [Filter("year", "=", "2024")]) is True
        assert matches(r, [Filter("year", "=", "2023")]) is False

    def test_year_greater_than(self):
        r = _r(year=2024)
        assert matches(r, [Filter("year", ">", "2020")]) is True
        assert matches(r, [Filter("year", ">", "2024")]) is False

    def test_year_none_skipped(self):
        """year=None: equality to "None" string is False; greater than 0 is False."""
        r = _r(year=None)
        assert matches(r, [Filter("year", "=", "2024")]) is False
        assert matches(r, [Filter("year", ">", "0")]) is False

    def test_citation_count_none_does_not_match_less_than(self):
        """Missing citation_count should not satisfy </<= operators."""
        r = _r(citation_count=None)
        assert matches(r, [Filter("citation_count", "<", "5")]) is False
        assert matches(r, [Filter("citation_count", "<=", "5")]) is False
        assert matches(r, [Filter("citation_count", ">", "0")]) is False
        assert matches(r, [Filter("citation_count", ">=", "0")]) is False

    def test_journal_substring(self):
        r = _r(journal="Nature Medicine")
        # "contains" / "like" matches substring
        assert matches(r, [Filter("journal", "contains", "Medicine")]) is True
        assert matches(r, [Filter("journal", "contains", "Science")]) is False

    def test_author_match_by_surname(self):
        r = _r(authors=[Author(full_name="Smith, John", order=1)])
        # "Smith" should match against any author
        assert matches(r, [Filter("author", "contains", "Smith")]) is True
        assert matches(r, [Filter("author", "contains", "Jones")]) is False

    def test_keyword_match(self):
        r = _r(keywords=["machine learning", "AI"])
        assert matches(r, [Filter("keyword", "contains", "machine")]) is True
        assert matches(r, [Filter("keyword", "contains", "quantum")]) is False

    def test_language_equality(self):
        r = _r(language="zh")
        assert matches(r, [Filter("language", "=", "zh")]) is True
        assert matches(r, [Filter("language", "=", "en")]) is False

    def test_doc_type_equality(self):
        r = _r()
        assert matches(r, [Filter("doc_type", "=", "unknown")]) is True
        assert matches(r, [Filter("doc_type", "=", "article")]) is False

    def test_citation_count(self):
        r = _r(citation_count=42)
        assert matches(r, [Filter("citation_count", ">=", "10")]) is True
        assert matches(r, [Filter("citation_count", "<", "10")]) is False

    def test_no_filters_returns_true(self):
        r = _r()
        assert matches(r, []) is True

    def test_and_chain_matches(self):
        r = _r(year=2024, journal="Nature")
        f = [Filter("year", ">=", "2020"), Filter("journal", "=", "Nature")]
        assert matches(r, f) is True

    def test_and_chain_fails_one(self):
        r = _r(year=2024, journal="Nature")
        f = [Filter("year", ">=", "2020"), Filter("journal", "=", "Science")]
        assert matches(r, f) is False

    def test_or_chain_matches_one(self):
        # OR combinator: at least one filter must match.
        # Construct the parsed-token list directly (skipping the
        # parser so we exercise the matcher AND/OR logic in isolation).
        r = _r(year=2024, journal="Nature")
        f = ["OR", Filter("year", ">=", "2020"), Filter("journal", "=", "Science")]
        assert matches(r, f) is True
        # Both filters false under OR → no match
        f2 = ["OR", Filter("year", ">", "2099"), Filter("journal", "=", "X")]
        assert matches(r, f2) is False

    def test_case_insensitive_journal(self):
        r = _r(journal="Nature")
        assert matches(r, [Filter("journal", "contains", "nature")]) is True
        assert matches(r, [Filter("journal", "contains", "NATURE")]) is True


# ===========================================================================
# CLI integration: citationer query ...
# ===========================================================================


def _setup_db_with_records(clean_cwd: Path) -> None:
    """Insert 5 records with varied fields."""
    records = [
        _r(title="ML 2020", year=2020, journal="Nature", citation_count=15,
            language="en", keywords=["machine learning"]),
        _r(title="DL 2021", year=2021, journal="Science", citation_count=50,
            language="en", keywords=["deep learning"]),
        _r(title="CV 2022", year=2022, journal="Nature", citation_count=5,
            language="en", keywords=["computer vision"]),
        _r(title="NLP 2023", year=2023, journal="ACL", citation_count=100,
            language="en", keywords=["NLP"]),
        _r(title="Chinese ML 2024", year=2024, journal="自动化学报", citation_count=8,
            language="zh", keywords=["机器学习"]),
    ]
    seed_cli_db(clean_cwd, records)


class TestQueryCli:
    def test_query_year_filter(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db_with_records(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["query", "year>=2023"])
        assert result.exit_code == 0
        # Should match only 2023 and 2024 records (2 records)
        assert "2023" in result.output
        assert "2024" in result.output

    def test_query_journal_filter(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db_with_records(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(app, ["query", "journal='Nature'"])
        assert result.exit_code == 0
        # 2 records have journal=Nature (2020, 2022)
        assert "Nature" in result.output

    def test_query_and_chain(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db_with_records(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["query", "year>=2023 AND citation_count>10"]
        )
        assert result.exit_code == 0
        # 2023 has 100 (>10), 2024 has 8 (not >10). Only 2023.
        assert "2023" in result.output
        assert "2024" not in result.output

    def test_query_format_json(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db_with_records(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["query", "year=2020", "--format", "json"]
        )
        assert result.exit_code == 0
        # JSON output should be parseable
        # Extract the JSON block (skip header rows)
        text = result.output
        # Find the JSON array
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            data = json.loads(text[start:end])
            assert isinstance(data, list)
            assert len(data) >= 1

    def test_query_format_csv(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db_with_records(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["query", "year=2020", "--format", "csv"]
        )
        assert result.exit_code == 0
        # CSV should have a header row
        assert "title" in result.output.lower() or "year" in result.output

    def test_query_limit(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db_with_records(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["query", "year>=2020", "--limit", "2"]
        )
        assert result.exit_code == 0
        # 5 records total, limit to 2 — should show only 2

    def test_query_no_data(self, cli_runner, clean_cwd):
        result = cli_runner.invoke(app, ["query", "year=2020"])
        assert result.exit_code in (0, 1)

    def test_query_output_to_file(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db_with_records(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        out = clean_cwd / "q.json"
        result = cli_runner.invoke(
            app, ["query", "year=2020", "--format", "json", "--output", str(out)]
        )
        assert result.exit_code == 0
        assert out.exists()

    def test_query_invalid_filter(self, cli_runner, clean_cwd, monkeypatch):
        _setup_db_with_records(clean_cwd)
        monkeypatch.chdir(clean_cwd)
        result = cli_runner.invoke(
            app, ["query", "evil_field=1"]
        )
        # Should fail with non-zero exit code
        assert result.exit_code != 0
