# RBAC & Data Classification

## Roles

| Role | Clearance | Allowed Tools |
|---|---|---|
| viewer | PUBLIC (1) | read_file, list_files, web_search |
| analyst | INTERNAL (2) | + search_code, git_status, read_log |
| manager | CONFIDENTIAL (3) | + run_shell, run_tests, get_env |
| admin | SECRET (4) | all tools including write_file, code_executor |

## Data Classification Levels

```python
PUBLIC       = 1   # anyone can see
INTERNAL     = 2   # analyst and above
CONFIDENTIAL = 3   # manager and above
SECRET       = 4   # admin only
```

Each `DataChunk` has a `.classification` int. `data_classifier` strips chunks above the user's clearance before any LLM call.

## Enforcement Points

1. `rbac_guard_node` — sets `allowed_tools` and `clearance_level` in state
2. `intent_guard_node` — keyword match: write/exec keywords + role missing tool → block
3. `human_approval_node` — interrupt() for intents: `code_write`, `infrastructure_write`, or destructive keywords (delete, rm, drop…)
4. Agent nodes — filter tool list from `ALL_TOOLS` by `state.allowed_tools` before binding to LLM
5. Agent prompts — LLM explicitly told: if tool not available, refuse (don't answer as plain text)

## Adding a New Role

Edit `security/rbac.py`:

```python
"ops": RolePolicy(
    name="ops",
    clearance_ceiling=Clearance.CONFIDENTIAL,
    allowed_tools=frozenset({
        "read_file", "list_files", "run_shell", "git_status",
    }),
),
```
