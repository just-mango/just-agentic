"""Tests for supervisor routing logic — loop detection, fallback, iteration cap."""

import pytest
from graph.supervisor import _parse_decision, MAX_ITERATIONS
from graph.nodes.intent_guard import intent_guard_node


class TestParseDecision:
    def test_valid_json_parsed(self):
        raw = '{"next_agent": "devops", "intent": "infrastructure_write", "confidence": 0.9, "reason": "Docker task", "goal_for_agent": "Create Dockerfile", "done": false}'
        d = _parse_decision(raw)
        assert d["next_agent"]   == "devops"
        assert d["intent"]       == "infrastructure_write"
        assert d["confidence"]   == 0.9
        assert d["done"]         is False

    def test_json_in_markdown_code_block(self):
        raw = '```json\n{"next_agent": "backend", "intent": "code_read", "confidence": 0.8, "reason": "x", "goal_for_agent": "y", "done": false}\n```'
        d = _parse_decision(raw)
        assert d["next_agent"] == "backend"

    def test_unknown_agent_sets_done_true(self):
        raw = '{"next_agent": "unknown_agent", "intent": "x", "confidence": 0.5, "reason": "", "goal_for_agent": "", "done": false}'
        d = _parse_decision(raw)
        assert d["done"] is True

    def test_finish_agent_sets_done_true(self):
        raw = '{"next_agent": "finish", "intent": "info_request", "confidence": 0.95, "reason": "done", "goal_for_agent": "answer", "done": false}'
        d = _parse_decision(raw)
        assert d["done"] is True

    def test_invalid_json_falls_back_to_keyword_scan(self):
        d = _parse_decision("I think devops should handle this Docker issue")
        assert d["next_agent"] == "devops"
        assert d["done"]       is False

    def test_completely_unparseable_returns_done(self):
        d = _parse_decision("I have no idea what to do here")
        assert d["done"] is True

    def test_confidence_clamped_to_0_1(self):
        raw = '{"next_agent": "qa", "intent": "test_run", "confidence": 1.5, "reason": "", "goal_for_agent": "", "done": false}'
        d = _parse_decision(raw)
        assert d["confidence"] <= 1.0

    def test_confidence_clamped_below_zero(self):
        raw = '{"next_agent": "qa", "intent": "test_run", "confidence": -0.5, "reason": "", "goal_for_agent": "", "done": false}'
        d = _parse_decision(raw)
        assert d["confidence"] >= 0.0


class TestLoopDetection:
    def test_same_agent_three_times_triggers_loop(self):
        """supervisor_node should stop if same agent appears LOOP_WINDOW times."""
        from graph.supervisor import supervisor_node, LOOP_WINDOW
        routing_history = ["devops"] * LOOP_WINDOW

        state = {
            "messages":        [],
            "user_goal":       "fix docker",
            "user_role":       "admin",
            "user_department": "devops",
            "allowed_tools":   ["run_shell", "read_file"],
            "iteration":       3,
            "routing_history": routing_history,
            "retry_count":     {},
            "supervisor_log":  [],
            "status":          "working",
            "plan":            [],
            "working_memory":  {},
        }
        result = supervisor_node(state)
        assert result["status"] in ("done", "error")
        assert "routing_loop" in result.get("error", "")

    def test_max_iterations_stops_graph(self):
        from graph.supervisor import supervisor_node

        state = {
            "messages":        [],
            "user_goal":       "task",
            "user_role":       "admin",
            "user_department": "engineering",
            "allowed_tools":   ["read_file"],
            "iteration":       MAX_ITERATIONS,
            "routing_history": [],
            "retry_count":     {},
            "supervisor_log":  [],
            "status":          "working",
            "plan":            [],
            "working_memory":  {},
        }
        result = supervisor_node(state)
        assert result["status"] in ("done", "error")
