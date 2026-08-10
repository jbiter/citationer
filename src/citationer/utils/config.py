"""Configuration management for citationer."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM / DeepSeek API configuration."""

    api_key: str = ""
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    max_tokens: int = 4096
    temperature: float = 0.7


class PipelineStep(BaseModel):
    """A single step in an analysis pipeline."""

    command: str
    args: dict = Field(default_factory=dict)


class PipelineConfig(BaseModel):
    """Declarative analysis pipeline."""

    steps: list[PipelineStep] = []


class CitationerConfig(BaseModel):
    """Root configuration for citationer."""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    default_output_dir: str = "citationer_output"
    language: str = "auto"  # zh, en, auto
    title_similarity_high: float = 0.85
    title_similarity_low: float = 0.70

    @classmethod
    def load(cls, config_path: Path) -> CitationerConfig:
        """Load configuration from a YAML file.

        If the file doesn't exist, returns a default config.
        """
        if not config_path.exists():
            return cls()
        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.model_validate(data)

    def save(self, config_path: Path) -> None:
        """Save configuration to a YAML file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(
                self.model_dump(),
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )


def find_data_dir(start_dir: Path | None = None) -> Path:
    """Find the .citationer directory by walking up from start_dir.

    If not found, returns Path(".citationer") relative to cwd.
    """
    current = start_dir or Path.cwd()
    for parent in [current, *current.parents]:
        candidate = parent / ".citationer"
        if candidate.is_dir():
            return candidate
    return Path.cwd() / ".citationer"


def ensure_data_dir() -> Path:
    """Get or create the .citationer data directory."""
    data_dir = Path.cwd() / ".citationer"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_db_path() -> Path:
    """Get the path to the SQLite cache database."""
    return ensure_data_dir() / "cache.db"


def get_config_path() -> Path:
    """Get the path to the config file."""
    env_path = os.environ.get("CITATIONER_CONFIG_PATH")
    if env_path:
        return Path(env_path)
    return ensure_data_dir() / "config.yaml"


def get_output_dir() -> Path:
    """Get the default output directory."""
    env_dir = os.environ.get("CITATIONER_OUTPUT_DIR")
    if env_dir:
        return Path(env_dir)
    return Path.cwd() / "citationer_output"


def load_api_key() -> str:
    """Load the LLM API key from environment or config.

    Environment variables (highest priority):
        CITATIONER_LLM_API_KEY  (or DEEPSEEK_API_KEY for backward compat)
    """
    # 1. Environment variable (new generic name)
    env_key = os.environ.get("CITATIONER_LLM_API_KEY", "")
    if env_key:
        return env_key

    # 2. Environment variable (legacy DeepSeek-specific name)
    env_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if env_key:
        return env_key

    # 3. Check config file
    config_path = get_config_path()
    if config_path.exists():
        config = CitationerConfig.load(config_path)
        if config.llm.api_key:
            return config.llm.api_key

    return ""


def load_llm_config() -> dict:
    """Load the full LLM configuration from environment and config file.

    Priority: env vars > config file > defaults.

    Supported environment variables:
        CITATIONER_LLM_API_KEY     (or DEEPSEEK_API_KEY)
        CITATIONER_LLM_MODEL
        CITATIONER_LLM_BASE_URL
        CITATIONER_LLM_TEMPERATURE
        CITATIONER_LLM_MAX_TOKENS

    Returns a dict with keys: api_key, model, base_url, temperature, max_tokens.
    """
    # Defaults
    result: dict = {
        "api_key": "",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
        "temperature": 0.3,
        "max_tokens": 4096,
    }

    # Load from config file first (lowest priority)
    config_path = get_config_path()
    if config_path.exists():
        cfg = CitationerConfig.load(config_path)
        if cfg.llm.api_key:
            result["api_key"] = cfg.llm.api_key
        if cfg.llm.model:
            result["model"] = cfg.llm.model
        if cfg.llm.base_url:
            result["base_url"] = cfg.llm.base_url
        result["temperature"] = cfg.llm.temperature
        result["max_tokens"] = cfg.llm.max_tokens

    # Override with environment variables (highest priority)
    env_map = {
        "api_key": ("CITATIONER_LLM_API_KEY", "DEEPSEEK_API_KEY"),
        "model": ("CITATIONER_LLM_MODEL",),
        "base_url": ("CITATIONER_LLM_BASE_URL",),
        "temperature": ("CITATIONER_LLM_TEMPERATURE",),
        "max_tokens": ("CITATIONER_LLM_MAX_TOKENS",),
    }
    for key, env_names in env_map.items():
        for name in env_names:
            val = os.environ.get(name, "")
            if val:
                if key in ("temperature",):
                    try:
                        result[key] = float(val)
                    except ValueError:
                        pass
                elif key in ("max_tokens",):
                    try:
                        result[key] = int(val)
                    except ValueError:
                        pass
                else:
                    result[key] = val
                break  # first env var wins

    return result
