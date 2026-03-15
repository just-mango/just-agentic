# Tools

## Available Tools

| Tool | Description | Min Role |
|---|---|---|
| `read_file` | Read UTF-8 file (redacted if above clearance) | viewer |
| `list_files` | List directory contents | viewer |
| `web_search` | DuckDuckGo search (no API key required) | viewer |
| `search_code` | Grep keyword in files | analyst |
| `git_status` | Run git status | analyst |
| `read_log` | Read log file tail (redacted if above clearance) | analyst |
| `get_env` | Read env variable | manager |
| `run_shell` | Run shell command | manager |
| `run_tests` | Run test command | manager |
| `write_file` | Write/overwrite file | admin |
| `code_executor` | Execute Python snippet | admin |

Effective tool access = `role.allowed_tools ∩ dept.permitted_tools`. See [rbac.md](rbac.md).

## Safety Layer (`tools/_safety.py`)

All tools pass through safety checks before execution:

- **Path allowlist** — paths must be under `WORKSPACE_ROOT`, blocks `/etc`, `/sys`, `/proc`, `/dev`
- **Command blocklist** — blocks destructive patterns: `rm -rf /`, `:(){ :|:& };:`, `dd if=`, `mkfs`, etc.
- **Timeout** — all shell/exec tools have a timeout (default 30s)
- **Logging** — every tool call logged with timestamp, tool name, args to `tool_calls.log`

## Output Classification (`security/output_classifier.py`)

`read_file` and `read_log` run their output through `check_output_clearance()` before returning to the LLM.

**Path-based rules:**

| Path pattern | Classification |
|---|---|
| `.env`, `*.env` | CONFIDENTIAL |
| `secrets/*.key`, `*.pem`, `*.p12` | SECRET |
| `config/*.yaml`, `config/*.json` | INTERNAL |
| `*.log` | INTERNAL |

**Content-based rules:**

| Content pattern | Classification |
|---|---|
| `-----BEGIN PRIVATE KEY` | SECRET |
| `password=`, `passwd=` | CONFIDENTIAL |
| `token=Bearer`, `Authorization: Bearer` | CONFIDENTIAL |
| `api_key=`, `apikey=` | CONFIDENTIAL |

If the classified level exceeds the user's `clearance_level`, the content is replaced with a redaction notice.

## Permission Decorator (`tools/_permission.py`)

```python
@tool
@permission_required("write_file")
def write_file(path: str, content: str) -> str: ...
```

Uses ContextVars (`_role_ctx`, `_dept_ctx`, `_clearance_ctx`) set by agent nodes via `set_role_context()`. Checks `effective_tools(role, dept)` — not just role alone.

## Adding a New Tool

1. Create the function in `tools/` with `@tool` and `@permission_required("tool_name")` decorators
2. Register in `tools/__init__.py` → `ALL_TOOLS` list
3. Assign minimum role in `security/rbac.py` (role policies + relevant dept policies)
4. Add test coverage in `tests/test_permission.py`

## Workspace Root

All file operations are restricted to `WORKSPACE_ROOT` (set in `.env`).

```
WORKSPACE_ROOT=/absolute/path/to/your/project
```
