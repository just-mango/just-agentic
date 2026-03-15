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
  → audit_log               write immutable JSONL record
END
```

Agents loop: `supervisor → human_approval → agent → supervisor` until `done=True` or max iterations.

## Defense in Depth

| Layer | Node | Blocks |
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

## Module Map

```
main.py                          CLI entry — login (JWT/dev), stream, interrupt handling
graph/
  secure_graph.py                builds and compiles the LangGraph graph (SqliteSaver)
  state.py                       AgentState TypedDict — single unified state (25+ fields)
  supervisor.py                  routing logic + intent/confidence/retry/loop detection
  agents/
    backend.py                   code, API, bug fix
    devops.py                    Docker, env, CI/CD
    qa.py                        test, log, verify
  nodes/
    rbac_guard.py                JWT + plain credential validation
    department_guard.py          role ∩ dept tool intersection, clearance cap
    data_classifier.py           clearance filtering for DataChunks
    intent_guard.py              deterministic pre-check (write/exec patterns)
    prompt_injection_guard.py    15+ regex patterns for injection detection
    human_approval.py            interrupt() gate for dangerous actions
    audit_log.py                 writes audit.jsonl
security/
  rbac.py                        roles + departments → tools + clearance ceiling
  classification.py              DataChunk + filter_by_clearance
  jwt_auth.py                    JWT decode/encode (PyJWT HS256), UserContext dataclass
  output_classifier.py           classifies tool output by file path + content patterns
  audit.py                       AuditLogger (JSONL + PostgreSQL stub)
tools/
  shell.py                       run_shell
  file_ops.py                    read_file, write_file, list_files, search_code, read_log
  code_exec.py                   code_executor
  web_search.py                  web_search
  _permission.py                 @permission_required decorator + ContextVars
  _safety.py                     path allowlist + command blocklist
llm/
  adapter.py                     LLMAdapter — OpenAI / OpenRouter / Anthropic / Ollama / vLLM
config/
  prompts.py                     system prompts for all agents
tests/
  test_rbac.py                   roles, depts, effective_tools, effective_clearance (26 tests)
  test_permission.py             @permission_required with role+dept (9 tests)
  test_prompt_injection.py       blocked patterns + safe inputs (27 tests)
  test_output_classifier.py      path/content classification (14 tests)
  test_intent_guard.py           write/exec blocking (13 tests)
  test_department_guard.py       tool reduction + clearance capping (10 tests)
  test_supervisor_routing.py     parse_decision, loop detection, max iterations (10 tests)
  test_jwt_auth.py               decode_token, make_dev_token, rbac_guard JWT path (18 tests)
```
