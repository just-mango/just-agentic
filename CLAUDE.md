# just-agentic

Secure multi-agent system using LangGraph + OpenAI. Supervisor routes tasks to Backend / DevOps / QA agents with RBAC, department-based access control, data classification, prompt injection detection, and human approval for dangerous actions.

Runs as a **CLI** or **FastAPI + SSE API** (with Next.js frontend).

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY, DATABASE_URL
python main.py          # CLI mode
uvicorn api.main:app    # API mode
```

## Graph Flow

```
rbac_guard → department_guard → data_classifier → intent_guard → prompt_injection_guard
  → supervisor → human_approval → [backend | devops | qa] → supervisor → audit_log
```

- **Agents**: `backend` (code), `devops` (Docker/env/CI), `qa` (tests/logs)
- **Supervisor**: routes by intent + confidence score, with fallback, retry, loop detection
- **Human approval**: `interrupt()` before `code_write` / `infrastructure_write` actions
- **Checkpoint**: PostgresSaver (PostgreSQL) or MemorySaver (fallback/testing)

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
| `main.py` | CLI entry — init_db, login, stream, interrupt handling |
| `api/main.py` | FastAPI app — startup, CORS, routers |
| `api/routers/agent.py` | POST /api/agent/chat + /resume — SSE streaming |
| `api/routers/auth.py` | POST /api/auth/login — JWT + dev modes |
| `graph/secure_graph.py` | Graph definition + PostgresSaver/MemorySaver |
| `graph/supervisor.py` | Routing + intent/confidence logic |
| `graph/state.py` | `AgentState` TypedDict — single unified state |
| `db/models.py` | SQLAlchemy ORM — User, Role, Dept, AuditRecord, ToolCallLog |
| `db/seed.py` | Default RBAC data (roles, departments, clearance levels) |
| `security/rbac.py` | Roles, departments, effective tools + clearance |
| `security/jwt_auth.py` | JWT decode/encode (PyJWT, HS256) |
| `security/output_classifier.py` | Classifies tool output by path + content |
| `config/prompts.py` | System prompts for all agents |
| `llm/adapter.py` | LLM provider switch |

## Roles & Departments

| Role | Clearance | Tools |
|---|---|---|
| viewer | PUBLIC (1) | read_file, list_files, web_search |
| analyst | INTERNAL (2) | + search_code, git_status, read_log, query_db, scrape_page, scan_secrets |
| manager | CONFIDENTIAL (3) | + run_shell, run_tests, get_env |
| admin | SECRET (4) | all tools including write_file, code_executor |

Effective access = `role.allowed_tools ∩ dept.permitted_tools`, clearance = `min(role, dept)`.

## Database

`init_db()` runs at startup (both CLI and API) — creates tables and seeds default RBAC data.

```
db/
  models.py     ORM: ClearanceLevel, Role, Department, User, AuditRecord, ToolCallLog
  session.py    Engine factory — PostgreSQL (prod) / SQLite (test), get_db() context manager
  seed.py       Idempotent default data seeding
```

Migrations via Alembic:

```bash
alembic upgrade head
```

## Environment

```bash
LLM_PROVIDER=openai          # openai | openrouter | anthropic | ollama | vllm
OPENAI_API_KEY=sk-...
JWT_SECRET=your-secret-here
DATABASE_URL=postgresql://user:pass@localhost:5432/just_agentic
MAX_ITERATIONS=8
CONFIDENCE_THRESHOLD=0.55
WORKSPACE_ROOT=/path/to/project
CHECKPOINT_BACKEND=postgres  # postgres | memory
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/login` | JWT or dev login → returns access token |
| POST | `/api/agent/chat` | Start task — streams SSE events |
| POST | `/api/agent/resume/{thread_id}` | Resume after human approval interrupt |
| GET | `/health` | Health check |

SSE event types: `thread_id`, `agent_switch`, `message`, `approval_required`, `permission_denied`, `done`, `error`

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
- Every action is logged to `audit_records` table (append-only, never deleted)
- `init_db()` is idempotent — safe to call on every startup
