# just-agentic

Secure multi-agent CLI using LangGraph + OpenAI. Supervisor routes tasks to Backend / DevOps / QA agents with RBAC, department-based access control, data classification, prompt injection detection, and human approval for dangerous actions.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY
python main.py
```

## Graph Flow

```
rbac_guard → department_guard → data_classifier → intent_guard → prompt_injection_guard
  → supervisor → human_approval → [backend | devops | qa] → supervisor → audit_log
```

- **Agents**: `backend` (code), `devops` (Docker/env/CI), `qa` (tests/logs)
- **Supervisor**: routes by intent, confidence score, fallback, retry, loop detection
- **Human approval**: interrupts before `code_write` / `infrastructure_write` actions

## Auth Modes

```
[1] JWT token  — paste Bearer token; role/dept/clearance decoded from token
[2] Dev mode   — enter user_id / role / department manually
```

Set `JWT_SECRET` in `.env` to enable JWT mode. Generate a dev token:

```python
from security.jwt_auth import make_dev_token
print(make_dev_token("alice", "analyst", "engineering"))
```

## Key Files

| File | Purpose |
|---|---|
| `main.py` | CLI entry, interrupt handling, resume loop |
| `graph/secure_graph.py` | graph definition + SqliteSaver checkpoint |
| `graph/supervisor.py` | routing + intent/confidence logic |
| `graph/state.py` | `AgentState` — single unified state |
| `security/rbac.py` | roles, departments, effective tools + clearance |
| `security/jwt_auth.py` | JWT decode/encode (PyJWT, HS256) |
| `security/output_classifier.py` | classifies tool output by path + content |
| `config/prompts.py` | system prompts for all agents |
| `llm/adapter.py` | LLM provider switch |

## Roles & Departments

| Role | Clearance | Tools |
|---|---|---|
| viewer | PUBLIC (1) | read_file, list_files, web_search |
| analyst | INTERNAL (2) | + search_code, git_status, read_log |
| manager | CONFIDENTIAL (3) | + run_shell, run_tests, get_env |
| admin | SECRET (4) | all tools |

Effective access = `role.allowed_tools ∩ dept.permitted_tools`, clearance = `min(role, dept)`.

## Environment

```bash
LLM_PROVIDER=openai          # openai | openrouter | anthropic | ollama | vllm
OPENAI_API_KEY=sk-...
JWT_SECRET=your-secret-here
MAX_ITERATIONS=8
CONFIDENCE_THRESHOLD=0.55
WORKSPACE_ROOT=/path/to/project
CHECKPOINT_BACKEND=sqlite    # sqlite | memory
```

## Tests

```bash
python -m pytest tests/ -v   # 157 tests
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
