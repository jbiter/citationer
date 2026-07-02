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
    return ensure_data_dir() / "config.yaml"


def get_output_dir() -> Path:
    """Get the default output directory."""
    return Path.cwd() / "citationer_output"


def load_api_key() -> str:
    """Load the DeepSeek API key from environment or config."""
    # 1. Environment variable takes priority
    env_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if env_key:
        return env_key

    # 2. Check config file
    config_path = get_config_path()
    if config_path.exists():
        config = CitationerConfig.load(config_path)
        if config.llm.api_key:
            return config.llm.api_key

    return ""
