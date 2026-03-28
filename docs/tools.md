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
| `query_db` | Read-only SQL query (SELECT only, 200 row cap) | analyst |
| `scrape_page` | Fetch URL and return clean text (SSRF-safe) | analyst |
| `scan_secrets` | Detect hardcoded credentials in files | analyst |
| `get_env` | Read env variable | manager |
| `run_shell` | Run shell command | manager |
| `run_tests` | Run test command | manager |
| `write_file` | Write/overwrite file | admin |
| `code_executor` | Execute Python snippet | admin |

Effective tool access = `role.allowed_tools ∩ dept.permitted_tools`. See [rbac.md](rbac.md).

## Safety Layer (`tools/_safety.py`)

All tools pass through safety checks before execution:

- **Path allowlist** — paths must be under `WORKSPACE_ROOT`, blocks `/etc`, `/sys`, `/proc`, `/dev`, `/private/etc`
- **Command blocklist** — blocks destructive patterns: `rm -rf /`, `:(){ :|:& };:`, `dd if=`, `mkfs`, etc.
- **Timeout** — all shell/exec tools have a timeout (default 30s)
- **Tool call logging** — every call appended to `tool_call_logs` table with timestamp, user_id, tool_name, inputs, output snippet

## Output Classification (`security/output_classifier.py`)

`read_file` and `read_log` run output through `check_output_clearance()` before returning to the LLM.

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

If classified level exceeds the user's `clearance_level`, content is replaced with a redaction notice.

## New Tools Detail

### `query_db` (`tools/db_query.py`)
- Executes read-only SQL via psycopg2 against `DATABASE_URL`
- Blocks all mutating statements: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`
- Results capped at 200 rows
- Logs to `tool_call_logs` table

### `scrape_page` (`tools/scraper.py`)
- Fetches a URL and returns clean text (via BeautifulSoup)
- Supports optional CSS selector for targeted extraction
- **SSRF protection**: blocks AWS metadata (`169.254.169.254`), GCP metadata (`metadata.google.internal`), and other internal ranges
- 15-second timeout, output capped at 8,000 chars

### `scan_secrets` (`tools/secrets_scan.py`)
- Recursively scans files for hardcoded credentials
- Detects: AWS keys, OpenAI keys, Stripe keys, GitHub tokens, private keys, bearer tokens, passwords, DB URLs
- Skips: `.git/`, `node_modules/`, binaries, compiled files
- Findings capped at 100

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
3. Add minimum role to `security/rbac.py` (role + relevant department policies)
4. Add to Alembic migration if changing DB-stored RBAC data
5. Add test coverage in `tests/test_permission.py`

## Workspace Root

All file operations are restricted to `WORKSPACE_ROOT` (set in `.env`).

```
WORKSPACE_ROOT=/absolute/path/to/your/project
```
