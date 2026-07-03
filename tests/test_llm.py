"""Tests for the LLM client module."""


from citationer.llm.client import LLMClient, LLMConfig, LLMResponse
from citationer.models.record import Author, Institution, Record


def make_record(title="Test", abstract="Abstract text.", year=2024, **kwargs):
    """Helper to create test records."""
    return Record(title=title, abstract=abstract, year=year, **kwargs)


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
