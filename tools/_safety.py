"""Shared safety helpers: path allowlist, command blocklist, tool logging."""

import os
import time
import json
from pathlib import Path

# Paths that tools are NOT allowed to read/write
_BLOCKED_PATH_PREFIXES = [
    "/etc/shadow", "/etc/passwd", "/etc/sudoers",
    "/sys", "/proc", "/dev",
    "/private/etc",
]

# Shell command patterns that are never allowed
_BLOCKED_COMMAND_PATTERNS = [
    "rm -rf /",
    "rm -rf ~",
    "> /dev/sda",
    "mkfs",
    "dd if=",
    ":(){:|:&};:",  # fork bomb
]

_LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "tool_calls.log")


def check_path(path: str) -> str | None:
    """Return an error string if path is blocked, else None."""
    resolved = str(Path(path).resolve())
    for blocked in _BLOCKED_PATH_PREFIXES:
        if resolved.startswith(blocked):
            return f"BLOCKED: access to '{path}' is not allowed"
    return None


def check_command(command: str) -> str | None:
    """Return an error string if command matches a blocked pattern, else None."""
    lower = command.lower().strip()
    for pattern in _BLOCKED_COMMAND_PATTERNS:
        if pattern in lower:
            return f"BLOCKED: command matches unsafe pattern '{pattern}'"
    return None


def log_tool_call(tool_name: str, inputs: dict, output: str) -> None:
    """Append a tool call record to tool_calls.log."""
    record = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "tool": tool_name,
        "inputs": inputs,
        "output_snippet": output[:200],
    }
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass  # logging failure must never crash the tool
