import os
import subprocess
from langchain_core.tools import tool
from tools._safety import check_path, log_tool_call
from tools._permission import permission_required, _clearance_ctx
from security.output_classifier import check_output_clearance


@tool
def read_file(path: str) -> str:
    """Read the contents of a UTF-8 text file from the workspace."""
    blocked = check_path(path)
    if blocked:
        log_tool_call("read_file", {"path": path}, blocked)
        return blocked
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        redacted = check_output_clearance(path, content, _clearance_ctx.get())
        if redacted:
            log_tool_call("read_file", {"path": path}, redacted)
            return redacted
        log_tool_call("read_file", {"path": path}, content)
        return content
    except FileNotFoundError:
        out = f"ERROR: File not found: {path}"
        log_tool_call("read_file", {"path": path}, out)
        return out
    except Exception as e:
        out = f"ERROR: {e}"
        log_tool_call("read_file", {"path": path}, out)
        return out


@tool
@permission_required("write_file")
def write_file(path: str, content: str) -> str:
    """Write content to a file. Creates parent directories if needed. Overwrites existing files."""
    blocked = check_path(path)
    if blocked:
        log_tool_call("write_file", {"path": path}, blocked)
        return blocked
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        out = f"OK: Written {len(content)} chars to {path}"
        log_tool_call("write_file", {"path": path, "bytes": len(content)}, out)
        return out
    except Exception as e:
        out = f"ERROR: {e}"
        log_tool_call("write_file", {"path": path}, out)
        return out


@tool
def list_files(path: str = ".") -> str:
    """List files and directories at the given path. Defaults to current directory."""
    blocked = check_path(path)
    if blocked:
        log_tool_call("list_files", {"path": path}, blocked)
        return blocked
    try:
        entries = os.listdir(path)
        lines = []
        for entry in sorted(entries):
            full = os.path.join(path, entry)
            tag = "/" if os.path.isdir(full) else ""
            lines.append(f"{entry}{tag}")
        out = "\n".join(lines) if lines else "(empty directory)"
        log_tool_call("list_files", {"path": path}, out)
        return out
    except FileNotFoundError:
        out = f"ERROR: Directory not found: {path}"
        log_tool_call("list_files", {"path": path}, out)
        return out
    except Exception as e:
        out = f"ERROR: {e}"
        log_tool_call("list_files", {"path": path}, out)
        return out


@tool
def search_code(keyword: str, path: str = ".") -> str:
    """Search for a keyword in source code files under the given path.

    Uses grep to find occurrences. Returns file:line matches.
    """
    blocked = check_path(path)
    if blocked:
        log_tool_call("search_code", {"keyword": keyword, "path": path}, blocked)
        return blocked
    try:
        result = subprocess.run(
            ["grep", "-rn", "--include=*.py", "--include=*.go", "--include=*.ts",
             "--include=*.js", "--include=*.java", "--include=*.sh",
             keyword, path],
            capture_output=True, text=True, timeout=15,
        )
        out = result.stdout.strip() or "(no matches found)"
        if result.stderr:
            out += f"\nSTDERR: {result.stderr.strip()}"
        log_tool_call("search_code", {"keyword": keyword, "path": path}, out)
        return out
    except subprocess.TimeoutExpired:
        return "ERROR: search_code timed out after 15 seconds"
    except Exception as e:
        return f"ERROR: {e}"


@tool
def read_log(path: str, tail: int = 100) -> str:
    """Read the last N lines of a log file. Default: last 100 lines."""
    blocked = check_path(path)
    if blocked:
        log_tool_call("read_log", {"path": path}, blocked)
        return blocked
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        out = "".join(lines[-tail:])
        redacted = check_output_clearance(path, out, _clearance_ctx.get())
        if redacted:
            log_tool_call("read_log", {"path": path}, redacted)
            return redacted
        log_tool_call("read_log", {"path": path, "tail": tail}, out)
        return out or "(empty log)"
    except FileNotFoundError:
        out = f"ERROR: Log file not found: {path}"
        log_tool_call("read_log", {"path": path}, out)
        return out
    except Exception as e:
        return f"ERROR: {e}"
