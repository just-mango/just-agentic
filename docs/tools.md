# Tools

## Available Tools

| Tool | Description | Min Role |
|---|---|---|
| `read_file` | Read UTF-8 file | viewer |
| `list_files` | List directory | viewer |
| `web_search` | DuckDuckGo search | viewer |
| `search_code` | Grep keyword in files | analyst |
| `git_status` | Run git status | analyst |
| `read_log` | Read log file tail | analyst |
| `get_env` | Read env variable | manager |
| `run_shell` | Run shell command | manager |
| `run_tests` | Run test command | manager |
| `write_file` | Write/overwrite file | admin |
| `code_executor` | Execute Python snippet | admin |

## Safety Layer (`tools/_safety.py`)

All tools pass through safety checks:

- **Path allowlist** — paths must be under `WORKSPACE_ROOT`, blocks `/etc`, `/sys`, `/proc`, `/dev`
- **Command blocklist** — blocks destructive patterns: `rm -rf /`, `:(){ :|:& };:`, `dd if=`, `mkfs`, etc.
- **Timeout** — all shell/exec tools have a timeout (default 30s)
- **Logging** — every tool call is logged with timestamp, tool name, args

## Adding a New Tool

1. Create the function in `tools/` with `@tool` decorator
2. Register in `tools/__init__.py` → `ALL_TOOLS` list
3. Assign minimum role in `security/rbac.py`

## Workspace Root

All file operations are restricted to `WORKSPACE_ROOT` (set in `.env`).

```
WORKSPACE_ROOT=/absolute/path/to/your/project
```
