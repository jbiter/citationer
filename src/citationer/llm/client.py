"""DeepSeek LLM client with caching and privacy-preserving data sanitization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING

from citationer.models.record import Record
from citationer.utils.config import get_db_path
from citationer.utils.database import CitationDatabase

if TYPE_CHECKING:
    from openai import OpenAI


@dataclass
class LLMResponse:
    """Result from an LLM query."""

    content: str
    model: str
    tokens_used: int = 0
    cached: bool = False


@dataclass
class LLMConfig:
    """Configuration for an LLM client."""

    api_key: str = ""
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    temperature: float = 0.3
    max_tokens: int = 4096


class LLMClient:
    """Client for DeepSeek / OpenAI-compatible LLM API.

    Features:
    - Privacy: only titles + abstracts are sent (no author/affiliation/DOI)
    - Caching: responses cached in SQLite llm_cache table by input hash
    - Dry-run: preview prompts without making API calls
    """

    def __init__(self, config: LLMConfig | None = None) -> None:
        self._config = config or LLMConfig()
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        if self._client is None:
            from openai import OpenAI

            if not self._config.api_key:
                raise ValueError(
                    "LLM API key not configured. "
                    "Edit .citationer/config.yaml and set llm.api_key, "
                    "or set the CITATIONER_LLM_API_KEY environment variable."
                )
            self._client = OpenAI(
                api_key=self._config.api_key,
                base_url=self._config.base_url,
            )
        return self._client

    # ------------------------------------------------------------------
    # Sanitization
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_records(records: list[Record]) -> list[dict]:
        """Extract only title + abstract for privacy.

        Strips: author names, emails, affiliations, institutions, DOIs,
        source filenames, and any other personally identifiable metadata.
        """
        sanitized: list[dict] = []
        for r in records:
            item: dict = {"title": r.title}
            if r.abstract:
                item["abstract"] = r.abstract
            # Include year for temporal context when relevant
            if r.year:
                item["year"] = r.year
            sanitized.append(item)
        return sanitized

    # ------------------------------------------------------------------
    # Caching
    # ------------------------------------------------------------------

    @staticmethod
    def _get_cache_key(prompt: str, sanitized: list[dict]) -> str:
        """Generate a deterministic cache key from prompt + sanitized input."""
        content = prompt + json.dumps(
            sanitized, sort_keys=True, ensure_ascii=False
        )
        return sha256(content.encode("utf-8")).hexdigest()

    def _check_cache(self, cache_key: str) -> str | None:
        """Check the SQLite cache for an existing response."""
        db_path = get_db_path()
        if not db_path.exists():
            return None
        db = CitationDatabase(db_path)
        db.initialize()
        try:
            return db.get_cached_llm_response(cache_key)
        finally:
            db.close()

    def _save_cache(
        self, cache_key: str, response: str, tokens: int
    ) -> None:
        """Save a response to the SQLite cache."""
        db_path = get_db_path()
        db = CitationDatabase(db_path)
        db.initialize()
        try:
            db.save_llm_cache(
                cache_key, response, tokens, self._config.model
            )
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    # Max input characters sent to the LLM (≈ 50K tokens, safe for all models).
    # Each ~4 chars ≈ 1 token. Records beyond this limit are truncated with a note.
    DEFAULT_MAX_INPUT_CHARS: int = 200_000

    def query(
        self,
        prompt: str,
        records: list[Record],
        *,
        dry_run: bool = False,
        system_prompt: str = "You are a bibliometric analysis assistant.",
        max_input_chars: int | None = None,
    ) -> LLMResponse:
        """Send sanitized records with a prompt to the LLM.

        Args:
            prompt: The user-facing instruction for the LLM.
            records: List of records to analyze (will be sanitized).
            dry_run: If True, preview the prompt + sanitized data without API call.
            system_prompt: System-level instruction for the LLM.
            max_input_chars: Max characters to send (≈ tokens × 4).
                Defaults to 200K. Set to 0 to send all records (no limit).
        """
        sanitized = self._sanitize_records(records)
        limit = max_input_chars if max_input_chars is not None else self.DEFAULT_MAX_INPUT_CHARS

        # Truncate if records data exceeds the character budget.
        # Prompt and system message are always sent; only records are truncated.
        if limit > 0:
            budget = limit - len(prompt) - len(system_prompt) - 200
            kept: list[dict] = []
            used = 0
            for item in sanitized:
                item_len = len(json.dumps(item, ensure_ascii=False))
                if used + item_len <= budget:
                    kept.append(item)
                    used += item_len
                else:
                    break
            if len(kept) < len(sanitized):
                kept.append({
                    "_truncated": True,
                    "_note": (
                        f"Input truncated: {len(kept)} of {len(sanitized)} records "
                        f"sent (limit ≈ {limit // 4} tokens). "
                        "Use --max-records to control this."
                    ),
                })
            sanitized = kept

        if dry_run:
            preview = {
                "system": system_prompt,
                "prompt": prompt,
                "records_count": len(sanitized),
                "sample_records": sanitized[:3],
                "total_chars": sum(
                    len(json.dumps(r, ensure_ascii=False)) for r in sanitized
                ),
            }
            return LLMResponse(
                content=json.dumps(preview, ensure_ascii=False, indent=2),
                model=self._config.model,
                tokens_used=0,
                cached=False,
            )

        # Check cache
        cache_key = self._get_cache_key(prompt, sanitized)
        cached_response = self._check_cache(cache_key)
        if cached_response:
            return LLMResponse(
                content=cached_response,
                model=self._config.model,
                tokens_used=0,
                cached=True,
            )

        # Build messages
        user_content = prompt + "\n\n" + json.dumps(
            sanitized, ensure_ascii=False, indent=2
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        # API call
        client = self._get_client()
        try:
            from openai import OpenAIError
        except ImportError:  # pragma: no cover
            openai_error = Exception
        else:
            openai_error = OpenAIError
        try:
            response = client.chat.completions.create(
                model=self._config.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=self._config.temperature,
                max_tokens=self._config.max_tokens,
            )
        except openai_error as exc:
            return LLMResponse(
                content=f"LLM API 调用失败: {exc}",
                model=self._config.model,
                tokens_used=0,
                cached=False,
            )

        content = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0

        # Cache the result
        self._save_cache(cache_key, content, tokens)

        return LLMResponse(
            content=content,
            model=self._config.model,
            tokens_used=tokens,
            cached=False,
        )

    def get_cache_stats(self) -> dict:
        """Get LLM cache statistics from the database."""
        db_path = get_db_path()
        if not db_path.exists():
            return {"cached_entries": 0, "total_tokens_used": 0}
        db = CitationDatabase(db_path)
        db.initialize()
        try:
            return db.get_llm_cache_stats()
        finally:
            db.close()
