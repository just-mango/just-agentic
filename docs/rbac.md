# RBAC & Data Classification

## Roles

| Role | Clearance | Allowed Tools |
|---|---|---|
| viewer | PUBLIC (1) | read_file, list_files, web_search |
| analyst | INTERNAL (2) | + search_code, git_status, read_log |
| manager | CONFIDENTIAL (3) | + run_shell, run_tests, get_env |
| admin | SECRET (4) | all tools including write_file, code_executor |

## Departments

| Department | Max Clearance | Permitted Tools |
|---|---|---|
| engineering | CONFIDENTIAL (3) | most tools except write_file, code_executor |
| devops | CONFIDENTIAL (3) | shell, file ops, git, env |
| qa | INTERNAL (2) | read, search, tests, logs |
| data | SECRET (4) | all tools |
| security | SECRET (4) | all tools |
| all | SECRET (4) | all tools (no dept restriction) |

## Effective Access

```
effective_tools     = role.allowed_tools  ∩  dept.permitted_tools
effective_clearance = min(role.clearance_ceiling, dept.max_clearance)
```

Examples:
- `admin` + `qa` → clearance capped at INTERNAL (2), write_file removed
- `manager` + `engineering` → clearance CONFIDENTIAL (3), run_shell available
- `analyst` + `data` → clearance INTERNAL (2) (role caps it), no shell/write

Enforced by `department_guard` node immediately after `rbac_guard`.

## Data Classification Levels

```python
PUBLIC       = 1   # anyone can see
INTERNAL     = 2   # analyst and above
CONFIDENTIAL = 3   # manager and above
SECRET       = 4   # admin only
```

Each `DataChunk` has a `.classification` int. `data_classifier` strips chunks above the user's effective clearance before any LLM call.

## JWT Authentication

Token payload: `{"sub": "<user_id>", "role": "<role>", "dept": "<dept>", "exp": <timestamp>}`

```python
from security.jwt_auth import make_dev_token, decode_token

# Generate a dev token (never use in production)
token = make_dev_token("alice", "analyst", "engineering", expires_in_hours=8)

# Decode and validate
ctx = decode_token(token)
# UserContext(user_id="alice", role="analyst", department="engineering", clearance_level=2)
```

Set `JWT_SECRET` in `.env`. `decode_token` requires `sub`, `role`, and `exp` claims.

## Enforcement Points

1. `rbac_guard_node` — validates JWT or plain credentials, sets `allowed_tools` + `clearance_level`
2. `department_guard_node` — intersects role ∩ dept tools, caps clearance to dept ceiling
3. `intent_guard_node` — keyword match: write/exec keywords + role missing tool → block
4. `human_approval_node` — `interrupt()` for intents: `code_write`, `infrastructure_write`, or destructive keywords
5. Agent nodes — filter `ALL_TOOLS` by `state.allowed_tools` before binding to LLM
6. `@permission_required` — tool-level last resort, uses `effective_tools(role, dept)` via ContextVars
7. `output_classifier` — redacts tool output whose path/content exceeds user's clearance

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

## Adding a New Department

Edit `security/rbac.py`:

```python
"infra": DepartmentPolicy(
    name="infra",
    max_clearance=Clearance.CONFIDENTIAL,
    permitted_tools=frozenset({
        "read_file", "list_files", "run_shell", "git_status", "get_env",
    }),
),
```
