import subprocess
import tempfile
import os
from langchain_core.tools import tool
from tools._safety import log_tool_call
from tools._permission import permission_required


@tool
@permission_required("execute_python")
def execute_python(code: str) -> str:
    """Execute a Python code snippet and return the output.

    Runs in an isolated temp file. Use print() to see output.
    Timeout: 30 seconds.
    """
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        result = subprocess.run(
            ["python3", tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = ""
        if result.stdout:
            output += f"OUTPUT:\n{result.stdout}"
        if result.stderr:
            output += f"\nERROR:\n{result.stderr}"
        output = output or "(no output)"
        output += f"\nEXIT CODE: {result.returncode}"
    except subprocess.TimeoutExpired:
        output = "ERROR: Code execution timed out after 30 seconds"
    except Exception as e:
        output = f"ERROR: {e}"
    finally:
        if tmp_path:
            os.unlink(tmp_path)

    log_tool_call("execute_python", {"code_snippet": code[:100]}, output)
    return output


@tool
def run_tests(command: str = "pytest -q") -> str:
    """Run a test suite and return the full output.

    Default: pytest -q
    Examples: "pytest -q", "go test ./...", "npm test"
    Timeout: 120 seconds.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}"
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        output = output or "(no output)"
        output += f"\nEXIT CODE: {result.returncode}"
    except subprocess.TimeoutExpired:
        output = "ERROR: Tests timed out after 120 seconds"
    except Exception as e:
        output = f"ERROR: {e}"

    log_tool_call("run_tests", {"command": command}, output)
    return output


@tool
def get_env(name: str) -> str:
    """Read an environment variable by name.

    Returns the value, or a message if not set.
    Never returns secrets in full — truncates values over 20 chars.
    """
    value = os.environ.get(name)
    if value is None:
        out = f"ENV '{name}' is not set"
    elif len(value) > 20:
        out = f"ENV '{name}' = {value[:4]}...{value[-4:]} (truncated, len={len(value)})"
    else:
        out = f"ENV '{name}' = {value}"
    log_tool_call("get_env", {"name": name}, out)
    return out
