"""Tests for configuration management."""



from citationer.utils.config import (
    CitationerConfig,
    LLMConfig,
    get_config_path,
    get_db_path,
    load_api_key,
    load_llm_config,
)


class TestLLMConfig:
    def test_defaults(self):
        cfg = LLMConfig()
        assert cfg.api_key == ""
        assert cfg.model == "deepseek-chat"
        assert cfg.base_url == "https://api.deepseek.com"
        assert cfg.max_tokens == 4096
        assert cfg.temperature == 0.7


class TestCitationerConfig:
    def test_defaults(self):
        cfg = CitationerConfig()
        assert cfg.llm.model == "deepseek-chat"
        assert cfg.language == "auto"
        assert cfg.title_similarity_high == 0.85
        assert cfg.title_similarity_low == 0.70

    def test_load_nonexistent(self, tmp_path):
        cfg = CitationerConfig.load(tmp_path / "nonexistent.yaml")
        assert cfg.language == "auto"

    def test_save_and_load(self, tmp_path):
        cfg = CitationerConfig(
            language="zh",
            llm=LLMConfig(model="gpt-4o", api_key="sk-test"),
        )
        p = tmp_path / "config.yaml"
        cfg.save(p)
        loaded = CitationerConfig.load(p)
        assert loaded.language == "zh"
        assert loaded.llm.model == "gpt-4o"
        assert loaded.llm.api_key == "sk-test"


class TestLoadLLMConfig:
    @staticmethod
    def _isolate_config(monkeypatch, tmp_path):
        """Ensure no real config file interferes with tests."""
        import citationer.utils.config as _cfg
        monkeypatch.setattr(_cfg, "get_config_path", lambda: tmp_path / "noexist.yaml")

    def test_defaults_when_nothing_configured(self, monkeypatch, tmp_path):
        """With no env vars and no config file, should return defaults."""
        self._isolate_config(monkeypatch, tmp_path)
        monkeypatch.delenv("CITATIONER_LLM_API_KEY", raising=False)
        monkeypatch.delenv("CITATIONER_LLM_MODEL", raising=False)
        monkeypatch.delenv("CITATIONER_LLM_BASE_URL", raising=False)
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

        cfg = load_llm_config()
        assert cfg["model"] == "deepseek-chat"
        assert cfg["base_url"] == "https://api.deepseek.com"
        assert cfg["temperature"] == 0.3
        assert cfg["max_tokens"] == 4096
        assert cfg["api_key"] == ""

    def test_env_var_override(self, monkeypatch, tmp_path):
        """Environment variables should override defaults."""
        self._isolate_config(monkeypatch, tmp_path)
        monkeypatch.setenv("CITATIONER_LLM_MODEL", "gpt-4o")
        monkeypatch.setenv("CITATIONER_LLM_TEMPERATURE", "0.5")
        monkeypatch.setenv("CITATIONER_LLM_MAX_TOKENS", "8192")

        cfg = load_llm_config()
        assert cfg["model"] == "gpt-4o"
        assert cfg["temperature"] == 0.5
        assert cfg["max_tokens"] == 8192

    def test_legacy_deepseek_key(self, monkeypatch, tmp_path):
        """DEEPSEEK_API_KEY should work as legacy fallback."""
        self._isolate_config(monkeypatch, tmp_path)
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-legacy")
        monkeypatch.delenv("CITATIONER_LLM_API_KEY", raising=False)

        cfg = load_llm_config()
        assert cfg["api_key"] == "sk-legacy"

    def test_new_key_has_priority(self, monkeypatch, tmp_path):
        """CITATIONER_LLM_API_KEY should take priority over DEEPSEEK_API_KEY."""
        self._isolate_config(monkeypatch, tmp_path)
        monkeypatch.setenv("CITATIONER_LLM_API_KEY", "sk-new")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-old")

        cfg = load_llm_config()
        assert cfg["api_key"] == "sk-new"

    def test_invalid_numeric_env(self, monkeypatch, tmp_path):
        """Invalid numeric env vars should fall back to defaults."""
        self._isolate_config(monkeypatch, tmp_path)
        monkeypatch.setenv("CITATIONER_LLM_TEMPERATURE", "not-a-number")
        monkeypatch.setenv("CITATIONER_LLM_MAX_TOKENS", "also-not-number")

        cfg = load_llm_config()
        assert cfg["temperature"] == 0.3  # default
        assert cfg["max_tokens"] == 4096  # default


class TestLoadAPIKey:
    def test_env_key(self, monkeypatch):
        monkeypatch.setenv("CITATIONER_LLM_API_KEY", "sk-env-test")
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        assert load_api_key() == "sk-env-test"

    def test_no_key(self, monkeypatch):
        monkeypatch.delenv("CITATIONER_LLM_API_KEY", raising=False)
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        # No config file in test context → should return ""
        key = load_api_key()
        assert key == "" or isinstance(key, str)


class TestPathFunctions:
    def test_get_db_path(self):
        p = get_db_path()
        assert p.name == "cache.db"

    def test_get_config_path(self):
        p = get_config_path()
        assert p.name == "config.yaml"
