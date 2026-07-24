"""Tests for the LLM client module."""


from unittest.mock import MagicMock

import pytest

from citationer.llm.client import LLMClient, LLMConfig, LLMResponse
from citationer.models.record import Author, Institution, Record
from tests._factories import make_record


class TestSanitization:
    def test_removes_authors(self):
        records = [
            make_record(
                title="Paper A",
                abstract="Research about AI.",
                authors=[
                    Author(
                        full_name="Smith, John",
                        email="jsmith@uni.edu",
                        affiliation="University X",
                    )
                ],
                doi="10.1000/test",
                source_file="data.xlsx",
            ),
        ]
        sanitized = LLMClient._sanitize_records(records)
        assert len(sanitized) == 1
        r = sanitized[0]
        assert r["title"] == "Paper A"
        assert r["abstract"] == "Research about AI."
        assert r["year"] == 2024
        # Critical: no PII/identifiable data
        assert "email" not in r
        assert "author" not in str(r).lower()
        assert "jsmith" not in str(r)
        assert "10.1000" not in str(r)
        assert "data.xlsx" not in str(r)

    def test_removes_institutions(self):
        records = [
            make_record(
                title="Paper B",
                institutions=[
                    Institution(name="Harvard University", country="USA")
                ],
                source_file="export.ciw",
            ),
        ]
        sanitized = LLMClient._sanitize_records(records)
        r = sanitized[0]
        assert "Harvard" not in str(r)
        assert "export.ciw" not in str(r)

    def test_handles_missing_fields(self):
        records = [
            Record(
                title="Minimal Paper",
            ),
        ]
        sanitized = LLMClient._sanitize_records(records)
        assert len(sanitized) == 1
        assert sanitized[0]["title"] == "Minimal Paper"
        assert "abstract" not in sanitized[0]
        assert "year" not in sanitized[0]

    def test_preserves_year(self):
        records = [
            make_record(title="Paper C", year=2023),
        ]
        sanitized = LLMClient._sanitize_records(records)
        assert sanitized[0]["year"] == 2023


class TestCacheKey:
    def test_same_input_same_key(self):
        records = [make_record(title="Paper A")]
        prompt = "Summarize these papers."
        key1 = LLMClient._get_cache_key(
            prompt, LLMClient._sanitize_records(records)
        )
        key2 = LLMClient._get_cache_key(
            prompt, LLMClient._sanitize_records(records)
        )
        assert key1 == key2

    def test_different_prompt_different_key(self):
        records = [make_record(title="Paper A")]
        sanitized = LLMClient._sanitize_records(records)
        key1 = LLMClient._get_cache_key("Summarize.", sanitized)
        key2 = LLMClient._get_cache_key("Classify.", sanitized)
        assert key1 != key2

    def test_different_records_different_key(self):
        r1 = [make_record(title="Paper A")]
        r2 = [make_record(title="Paper B")]
        key1 = LLMClient._get_cache_key(
            "Prompt", LLMClient._sanitize_records(r1)
        )
        key2 = LLMClient._get_cache_key(
            "Prompt", LLMClient._sanitize_records(r2)
        )
        assert key1 != key2

    def test_key_is_hex_string(self):
        records = [make_record(title="Paper A")]
        key = LLMClient._get_cache_key(
            "Prompt", LLMClient._sanitize_records(records)
        )
        assert len(key) == 64  # SHA256 hex
        assert all(c in "0123456789abcdef" for c in key)


class TestLLMConfig:
    def test_default_config(self):
        config = LLMConfig()
        assert config.model == "deepseek-chat"
        assert config.base_url == "https://api.deepseek.com"
        assert config.temperature == 0.3

    def test_custom_config(self):
        config = LLMConfig(
            api_key="sk-test",
            model="deepseek-reasoner",
            temperature=0.0,
        )
        assert config.api_key == "sk-test"
        assert config.model == "deepseek-reasoner"
        assert config.temperature == 0.0


class TestLLMResponse:
    def test_response_fields(self):
        r = LLMResponse(content="Hello", model="deepseek-chat", tokens_used=100)
        assert r.content == "Hello"
        assert r.model == "deepseek-chat"
        assert r.tokens_used == 100
        assert not r.cached

    def test_cached_response(self):
        r = LLMResponse(
            content="Cached result", model="deepseek-chat", tokens_used=0, cached=True
        )
        assert r.cached
        assert r.tokens_used == 0


class TestDryRun:
    def test_dry_run_bypasses_api_key(self):
        """Dry-run should work without a real API key."""
        client = LLMClient(LLMConfig(api_key="dry-run-skip"))
        records = [make_record(title="Test Paper")]
        response = client.query("Summarize.", records, dry_run=True)
        assert "DRY" not in response.content
        # Should contain preview info (JSON)
        assert "system" in response.content
        assert "records_count" in response.content
        assert response.tokens_used == 0

    def test_dry_run_shows_sanitized_data(self):
        """Dry-run output should only contain sanitized data."""
        client = LLMClient(LLMConfig(api_key="dry-run-skip"))
        records = [
            make_record(
                title="Paper A",
                abstract="Abstract text.",
                authors=[Author(full_name="Smith, John", email="s@uni.edu")],
                doi="10.1000/xyz",
            ),
        ]
        response = client.query("Analyze.", records, dry_run=True)
        # Should NOT contain PII
        assert "s@uni.edu" not in response.content
        assert "10.1000/xyz" not in response.content
        assert "Smith" not in response.content

    def test_dry_run_total_chars(self):
        """Dry-run should report total character count."""
        client = LLMClient(LLMConfig(api_key="dry-run-skip"))
        records = [make_record(title="Test", abstract="Some content here.")]
        response = client.query("Test.", records, dry_run=True)
        assert "total_chars" in response.content


class TestClientConstruction:
    def test_missing_api_key_raises(self):
        client = LLMClient(LLMConfig(api_key=""))
        with pytest.raises(ValueError, match="API key not configured"):
            client._get_client()

    def test_lazy_client_reused(self, monkeypatch):
        import sys
        from types import SimpleNamespace

        fake_openai = SimpleNamespace(OpenAI=MagicMock())
        monkeypatch.setitem(sys.modules, "openai", fake_openai)
        client = LLMClient(LLMConfig(api_key="sk-test"))
        c1 = client._get_client()
        c2 = client._get_client()
        assert c1 is c2
        fake_openai.OpenAI.assert_called_once()


class TestCache:
    def test_check_cache_no_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "citationer.llm.client.get_db_path", lambda: tmp_path / "missing.db"
        )
        client = LLMClient(LLMConfig(api_key=""))
        assert client._check_cache("any-key") is None

    def test_save_and_check_cache(self, tmp_path, monkeypatch):
        db_path = tmp_path / "cache.db"
        from citationer.utils.database import CitationDatabase

        CitationDatabase(db_path).initialize()
        monkeypatch.setattr("citationer.llm.client.get_db_path", lambda: db_path)

        client = LLMClient(LLMConfig(api_key="", model="stub"))
        client._save_cache("key-1", "cached response", 42)
        assert client._check_cache("key-1") == "cached response"

    def test_get_cache_stats_no_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "citationer.llm.client.get_db_path", lambda: tmp_path / "missing.db"
        )
        client = LLMClient(LLMConfig(api_key=""))
        assert client.get_cache_stats() == {
            "cached_entries": 0,
            "total_tokens_used": 0,
        }

    def test_get_cache_stats_with_entries(self, tmp_path, monkeypatch):
        db_path = tmp_path / "cache.db"
        from citationer.utils.database import CitationDatabase

        CitationDatabase(db_path).initialize()
        monkeypatch.setattr("citationer.llm.client.get_db_path", lambda: db_path)

        client = LLMClient(LLMConfig(api_key="", model="stub"))
        client._save_cache("key-1", "response 1", 10)
        client._save_cache("key-2", "response 2", 20)
        stats = client.get_cache_stats()
        assert stats["cached_entries"] == 2
        assert stats["total_tokens_used"] == 30


class TestQueryMocked:
    def test_query_cache_hit(self, tmp_path, monkeypatch):
        db_path = tmp_path / "cache.db"
        from citationer.utils.database import CitationDatabase

        CitationDatabase(db_path).initialize()
        monkeypatch.setattr("citationer.llm.client.get_db_path", lambda: db_path)

        client = LLMClient(LLMConfig(api_key="", model="stub"))
        records = [make_record(title="Cached")]
        sanitized = client._sanitize_records(records)
        cache_key = client._get_cache_key("Summarize.", sanitized)
        client._save_cache(cache_key, "cached result", 0)

        response = client.query("Summarize.", records)
        assert response.cached is True
        assert response.content == "cached result"
        assert response.tokens_used == 0

    def test_query_api_call(self, tmp_path, monkeypatch):
        db_path = tmp_path / "cache.db"
        from citationer.utils.database import CitationDatabase

        CitationDatabase(db_path).initialize()
        monkeypatch.setattr("citationer.llm.client.get_db_path", lambda: db_path)

        client = LLMClient(LLMConfig(api_key="sk-test", model="stub"))
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.choices = [MagicMock(message=MagicMock(content="AI reply"))]
        fake_response.usage = MagicMock(total_tokens=17)
        fake_client.chat.completions.create.return_value = fake_response
        client._client = fake_client

        response = client.query("Summarize.", [make_record(title="Paper")])
        assert response.cached is False
        assert response.content == "AI reply"
        assert response.tokens_used == 17
        fake_client.chat.completions.create.assert_called_once()
        # Cache should now contain the response
        assert client._check_cache(client._get_cache_key(
            "Summarize.", client._sanitize_records([make_record(title="Paper")])
        )) == "AI reply"

    def test_query_api_empty_content_and_usage(self, tmp_path, monkeypatch):
        db_path = tmp_path / "cache.db"
        from citationer.utils.database import CitationDatabase

        CitationDatabase(db_path).initialize()
        monkeypatch.setattr("citationer.llm.client.get_db_path", lambda: db_path)

        client = LLMClient(LLMConfig(api_key="sk-test", model="stub"))
        fake_client = MagicMock()
        fake_response = MagicMock()
        fake_response.choices = [MagicMock(message=MagicMock(content=None))]
        fake_response.usage = None
        fake_client.chat.completions.create.return_value = fake_response
        client._client = fake_client

        response = client.query("Go.", [make_record(title="Paper")])
        assert response.content == ""
        assert response.tokens_used == 0


class TestTruncation:
    def test_truncates_when_limit_exceeded(self):
        client = LLMClient(LLMConfig(api_key=""))
        records = [
            make_record(title=f"Very long title number {i}", abstract="x" * 500)
            for i in range(20)
        ]
        response = client.query("Summarize.", records, max_input_chars=200, dry_run=True)
        assert "_truncated" in response.content

    def test_no_truncation_when_limit_zero(self):
        client = LLMClient(LLMConfig(api_key=""))
        records = [
            make_record(title=f"Paper {i}", abstract="x" * 500)
            for i in range(10)
        ]
        response = client.query("Summarize.", records, max_input_chars=0, dry_run=True)
        assert "_truncated" not in response.content

    def test_no_truncation_when_all_fit(self):
        client = LLMClient(LLMConfig(api_key=""))
        records = [make_record(title="Short", abstract="abstract")]
        response = client.query("Summarize.", records, max_input_chars=10_000, dry_run=True)
        assert "_truncated" not in response.content
