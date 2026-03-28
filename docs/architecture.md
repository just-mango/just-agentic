# Architecture

## Graph Flow

```
START
  → rbac_guard              validate role/JWT, populate allowed_tools + clearance_level
  → department_guard        intersect role ∩ dept tools, cap clearance to dept ceiling
  → data_classifier         strip DataChunks above user's clearance level
  → intent_guard            deterministic keyword block before LLM (write/exec patterns)
  → prompt_injection_guard  regex scan for injection patterns (override, jailbreak, leak)
  → supervisor              route to specialist agent (LLM)
  → human_approval          interrupt() for dangerous actions (code_write / infra_write)
  → [backend|devops|qa]     specialist agent with filtered tools
  → supervisor              review result, route next or finish
  → audit_log               write immutable record to audit_records table
END
```

Agents loop: `supervisor → human_approval → agent → supervisor` until `done=True` or max iterations.

## Defense in Depth

| Layer | Node / Component | Blocks |
|---|---|---|
| 1 | `rbac_guard` | unknown roles, invalid/expired JWT tokens |
| 2 | `department_guard` | over-privileged tool access across departments |
| 3 | `data_classifier` | data above user's effective clearance level |
| 4 | `intent_guard` | write/exec keywords when tool not permitted (code, not LLM) |
| 5 | `prompt_injection_guard` | instruction override, role hijack, jailbreak, prompt leak |
| 6 | `human_approval` | dangerous actions via `interrupt()` |
| 7 | `@permission_required` | last-resort tool-level check (role ∩ dept) |

## Auth Modes

```
JWT mode  → rbac_guard calls decode_token(jwt_token)
            → validates exp, sub, role, dept claims
            → computes effective_clearance(role, dept)

Dev mode  → rbac_guard reads user_id/user_role/user_department directly from state
```

## Checkpoint Backend

| `DATABASE_URL` set? | Checkpointer |
|---|---|
| Yes | PostgresSaver (LangGraph) — persistent across restarts, multi-instance safe |
| No | MemorySaver — ephemeral, for testing/local dev |

## Module Map

```
main.py                          CLI entry — init_db, login (JWT/dev), stream, interrupt handling
api/
  main.py                        FastAPI app — CORS, startup init_db, health check
  deps.py                        Dependency injection — get_current_user() from Bearer token
  schemas.py                     Pydantic request/response models
  routers/
    auth.py                      POST /api/auth/login — JWT + dev modes
    agent.py                     POST /api/agent/chat — SSE streaming; POST /resume/{thread_id}
db/
  models.py                      ORM: ClearanceLevel, Role, Department, User, AuditRecord, ToolCallLog
  session.py                     Engine factory, get_db() context manager (PostgreSQL / SQLite)
  seed.py                        Idempotent default RBAC seeding
alembic/
  env.py                         Alembic config (auto-loads Base.metadata)
  versions/
    0001_initial_schema.py       Creates all tables
    0002_add_new_tools.py        Adds query_db, scan_secrets, scrape_page to roles/depts
graph/
  secure_graph.py                Builds and compiles the LangGraph graph (PostgresSaver/MemorySaver)
  state.py                       AgentState TypedDict — single unified state (25+ fields)
  supervisor.py                  Routing logic + intent/confidence/retry/loop detection
  agents/
    backend.py                   Code, API, bug fix
    devops.py                    Docker, env, CI/CD
    qa.py                        Test, log, verify
  nodes/
    rbac_guard.py                JWT + plain credential validation
    department_guard.py          Role ∩ dept tool intersection, clearance cap
    data_classifier.py           Clearance filtering for DataChunks
    intent_guard.py              Deterministic pre-check (write/exec patterns)
    prompt_injection_guard.py    15+ regex patterns for injection detection
    human_approval.py            interrupt() gate for dangerous actions
    audit_log.py                 Writes to audit_records table
security/
  rbac.py                        Roles + departments → tools + clearance ceiling
  classification.py              DataChunk + filter_by_clearance
  jwt_auth.py                    JWT decode/encode (PyJWT HS256), UserContext dataclass
  output_classifier.py           Classifies tool output by file path + content patterns
  audit.py                       AuditLogger singleton — writes to audit_records table
tools/
  shell.py                       run_shell
  file_ops.py                    read_file, write_file, list_files, search_code, read_log
  code_exec.py                   code_executor
  web_search.py                  web_search (DuckDuckGo, no API key)
  db_query.py                    query_db — read-only SQL (SELECT only, 200 row cap)
  scraper.py                     scrape_page — fetch URL → clean text (SSRF-safe)
  secrets_scan.py                scan_secrets — detect hardcoded credentials in files
  _permission.py                 @permission_required decorator + ContextVars
  _safety.py                     Path allowlist + command blocklist + tool_call_logs
llm/
  adapter.py                     LLMAdapter — OpenAI / OpenRouter / Anthropic / Ollama / vLLM
config/
  prompts.py                     System prompts for all agents
frontend/
  src/app/chat/                  Next.js chat UI
  src/components/                Chat components
  src/lib/                       SSE client, API helpers
tests/
  test_rbac.py                   Roles, depts, effective_tools, effective_clearance (26 tests)
  test_permission.py             @permission_required with role+dept (9 tests)
  test_prompt_injection.py       Blocked patterns + safe inputs (27 tests)
  test_output_classifier.py      Path/content classification (14 tests)
  test_intent_guard.py           Write/exec blocking (13 tests)
  test_department_guard.py       Tool reduction + clearance capping (10 tests)
  test_supervisor_routing.py     parse_decision, loop detection, max iterations (10 tests)
  test_jwt_auth.py               decode_token, make_dev_token, rbac_guard JWT path (18 tests)
```
