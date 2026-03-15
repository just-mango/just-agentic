# LLM Providers

Switch provider via `LLM_PROVIDER` in `.env`.

## Supported Providers

| Provider | Use Case | Key Env Vars |
|---|---|---|
| `openai` | Default / dev | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| `openrouter` | Dev, multi-model access | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` |
| `anthropic` | Claude models | `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` |
| `ollama` | Local, offline | `OLLAMA_MODEL` |
| `vllm` | Self-hosted prod | `VLLM_BASE_URL`, `VLLM_MODEL`, `VLLM_API_KEY` |

## Recommended Models

- **Dev**: `gpt-4o` or `anthropic/claude-sonnet-4-6` via OpenRouter
- **Prod (local)**: Ollama + `qwen2.5-coder:32b` or `qwen3.5:35b`

## Switching Provider

```bash
# .env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
```

No code changes needed — `llm/adapter.py` handles the switch.

## Adding a New Provider

Edit `llm/adapter.py`, add a new `elif` branch that returns a LangChain `BaseChatModel`.
