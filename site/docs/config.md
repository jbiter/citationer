# Configuration

Citationer stores settings in `.citationer/config.yaml` and supports environment variable overrides.

## CLI

```bash
citationer config show                # View all settings
citationer config set llm.api_key sk-xxx
citationer config set llm.model deepseek-chat
citationer config set llm.base_url https://api.openai.com/v1
citationer config set llm.temperature 0.5
citationer config set llm.max_tokens 8192
citationer config init                # Create default config
```

## LLM configuration

```yaml
# .citationer/config.yaml
llm:
  api_key: "sk-xxx"
  model: "deepseek-chat"
  base_url: "https://api.deepseek.com"
  temperature: 0.3
  max_tokens: 4096
```

### Supported providers

| Provider | base_url | model |
|----------|----------|-------|
| DeepSeek | `https://api.deepseek.com` | `deepseek-chat` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| Ollama (local) | `http://localhost:11434/v1` | `llama3` |

## Environment variables

Variables take priority over the config file:

| Variable | Maps to |
|----------|---------|
| `CITATIONER_LLM_API_KEY` | `llm.api_key` |
| `CITATIONER_LLM_MODEL` | `llm.model` |
| `CITATIONER_LLM_BASE_URL` | `llm.base_url` |
| `CITATIONER_LLM_TEMPERATURE` | `llm.temperature` |
| `CITATIONER_LLM_MAX_TOKENS` | `llm.max_tokens` |

Legacy `DEEPSEEK_API_KEY` is also supported as a fallback.

## Priority order

```
Environment variable  >  Config file  >  Default
```
