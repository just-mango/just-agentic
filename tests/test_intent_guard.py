"""Tests for intent guard node — deterministic write/exec blocking."""

import pytest
from langchain_core.messages import HumanMessage, AIMessage
from graph.nodes.intent_guard import intent_guard_node


def _state(text: str, allowed_tools: list[str]) -> dict:
    return {
        "messages":     [HumanMessage(content=text)],
        "user_goal":    text,
        "user_role":    "viewer",
        "allowed_tools": allowed_tools,
        "status":       "",
    }


VIEWER_TOOLS = ["read_file", "list_files", "web_search"]
ADMIN_TOOLS  = ["read_file", "write_file", "list_files", "run_shell",
                "execute_python", "run_tests", "web_search", "git_status",
                "search_code", "read_log", "get_env"]


class TestWriteBlocked:
    @pytest.mark.parametrize("text", [
        "create dockerfile",
        "write a config file",
        "generate file for me",
        "make new file",
        "save this to a file",
        "สร้างไฟล์",
        "เขียนไฟล์",
    ])
    def test_write_intent_blocked_for_viewer(self, text):
        result = intent_guard_node(_state(text, VIEWER_TOOLS))
        assert result["status"] == "permission_denied"

    def test_write_allowed_for_admin(self):
        result = intent_guard_node(_state("create dockerfile", ADMIN_TOOLS))
        assert result.get("status") != "permission_denied"


class TestExecBlocked:
    @pytest.mark.parametrize("text", [
        "run the tests",
        "execute this script",
        "deploy to production",
        "restart the service",
        "รัน pytest",
    ])
    def test_exec_intent_blocked_for_viewer(self, text):
        result = intent_guard_node(_state(text, VIEWER_TOOLS))
        assert result["status"] == "permission_denied"

    def test_exec_allowed_for_admin(self):
        result = intent_guard_node(_state("run the tests", ADMIN_TOOLS))
        assert result.get("status") != "permission_denied"


class TestSafeInputPasses:
    @pytest.mark.parametrize("text", [
        "show me the log file",
        "what is in requirements.txt",
        "explain this code",
        "search for auth in the codebase",
        "list files in the project",
    ])
    def test_read_only_passes_for_viewer(self, text):
        result = intent_guard_node(_state(text, VIEWER_TOOLS))
        assert result.get("status") != "permission_denied"


class TestAlreadyBlocked:
    def test_does_not_double_block(self):
        """If status is already permission_denied, node should not modify it."""
        state = _state("create file", VIEWER_TOOLS)
        state["status"] = "permission_denied"
        result = intent_guard_node(state)
        assert result["status"] == "permission_denied"
