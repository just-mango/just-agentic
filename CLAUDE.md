# just-agentic

Secure multi-agent CLI using LangGraph + OpenAI. Supervisor routes tasks to Backend / DevOps / QA agents with RBAC, data classification, and human approval for dangerous actions.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY
python main.py
```

## Graph Flow

```
rbac_guard → data_classifier → intent_guard → supervisor
  → human_approval → [backend | devops | qa] → supervisor → audit_log
```

- **Agents**: `backend` (code), `devops` (Docker/env/CI), `qa` (tests/logs)
- **Supervisor**: routes by intent, confidence score, fallback, retry, loop detection
- **Human approval**: interrupts before `code_write` / `infrastructure_write` actions

## Key Files

| File | Purpose |
|---|---|
| `main.py` | CLI entry, interrupt handling, resume loop |
| `graph/secure_graph.py` | graph definition |
| `graph/supervisor.py` | routing + intent/confidence logic |
| `graph/state.py` | `AgentState` — single unified state |
| `security/rbac.py` | roles, tools, clearance levels |
| `config/prompts.py` | system prompts for all agents |
| `llm/adapter.py` | LLM provider switch |

## Roles

`viewer` → `analyst` → `manager` → `admin` (increasing tool access + clearance)

## Environment

```bash
LLM_PROVIDER=openai          # openai | openrouter | anthropic | ollama | vllm
OPENAI_API_KEY=sk-...
MAX_ITERATIONS=8
CONFIDENCE_THRESHOLD=0.55
WORKSPACE_ROOT=/path/to/project
CHECKPOINT_BACKEND=sqlite    # sqlite | memory
```

## Docs

- [Architecture & module map](docs/architecture.md)
- [RBAC & data classification](docs/rbac.md)
- [Supervisor routing logic](docs/supervisor.md)
- [Tools & safety layer](docs/tools.md)
- [LLM providers](docs/llm-providers.md)

## Conventions

- State is immutable per node — always return `{**state, ...updated_fields}`
- Security is enforced in code (not prompt) — LLM is never trusted to enforce permissions
- Tools are filtered by `state.allowed_tools` before binding to any agent
- Every action is logged to `audit.jsonl`
