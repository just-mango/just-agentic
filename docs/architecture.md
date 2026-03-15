# Architecture

## Graph Flow

```
START
  → rbac_guard          validate role, populate allowed_tools
  → data_classifier     strip data above clearance level
  → intent_guard        deterministic block before LLM (keyword match)
  → supervisor          route to specialist agent (LLM)
  → human_approval      interrupt() for dangerous actions (write/exec)
  → [backend|devops|qa] specialist agent with filtered tools
  → supervisor          review result, route next or finish
  → audit_log           write immutable record
END
```

Agents loop: `supervisor → human_approval → agent → supervisor` until `done=True` or max iterations.

## Defense in Depth

| Layer | Node | Blocks |
|---|---|---|
| 1 | `rbac_guard` | unknown roles at entry |
| 2 | `data_classifier` | data above clearance level |
| 3 | `intent_guard` | write/exec if tool not allowed (code, not LLM) |
| 4 | `human_approval` | dangerous actions via interrupt() |
| 5 | agent prompts | LLM-level: refuse if tool missing |

## Module Map

```
main.py                   CLI entry — login, stream, interrupt handling
graph/
  secure_graph.py         builds and compiles the LangGraph graph
  state.py                AgentState TypedDict (single unified state)
  supervisor.py           routing logic + intent/confidence/retry/loop detection
  agents/
    backend.py            code, API, bug fix
    devops.py             Docker, env, CI/CD
    qa.py                 test, log, verify
  nodes/
    rbac_guard.py         RBAC validation
    data_classifier.py    clearance filtering
    intent_guard.py       deterministic pre-check
    human_approval.py     interrupt() gate
    audit_log.py          writes audit.jsonl
security/
  rbac.py                 role → tools + clearance ceiling
  classification.py       DataChunk + filter_by_clearance
  audit.py                AuditLogger (JSONL + PostgreSQL stub)
  jwt_auth.py             JWT decode stub
tools/
  shell.py                run_shell
  file_ops.py             read_file, write_file, list_files, search_code
  code_exec.py            code_executor
  web_search.py           web_search
  _safety.py              path allowlist + command blocklist
llm/
  adapter.py              LLMAdapter — OpenAI / OpenRouter / Anthropic / Ollama / vLLM
config/
  prompts.py              system prompts for all agents
```
