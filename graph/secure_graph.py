"""
Secure Multi-Agent Graph — Option A

Flow:
  START
    → rbac_guard_node          (validate role, populate allowed_tools)
    → data_classification_node (filter context by clearance level)
    → supervisor_node          (route to specialist agent)
    ↙            ↓           ↘
  backend      devops         qa
    ↘            ↓           ↙
    → supervisor_node          (review → route next or finish)
    → audit_log_node           (write immutable record)
  END

Defense in Depth:
  Layer 1 — rbac_guard:       blocks unknown roles at graph entry
  Layer 2 — data_classifier:  strips data above clearance before any LLM call
  Layer 3 — agent nodes:      filter allowed_tools before binding to LLM
"""

import os
import sqlite3
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from graph.state import AgentState
from graph.nodes.rbac_guard import rbac_guard_node
from graph.nodes.department_guard import department_guard_node
from graph.nodes.data_classifier import data_classification_node
from graph.nodes.intent_guard import intent_guard_node
from graph.nodes.prompt_injection_guard import prompt_injection_guard_node
from graph.nodes.human_approval import human_approval_node
from graph.nodes.audit_log import audit_log_node
from graph.supervisor import supervisor_node, route_after_supervisor
from graph.agents.backend import backend_node
from graph.agents.devops import devops_node
from graph.agents.qa import qa_node

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "8"))


# ---------------------------------------------------------------------------
# Entry routing — after RBAC check
# ---------------------------------------------------------------------------

def route_after_rbac(state: AgentState) -> str:
    if state.get("status") == "permission_denied":
        return "audit_log"
    return "data_classifier"


# ---------------------------------------------------------------------------
# Exit routing — supervisor decides done or routes to agent
# ---------------------------------------------------------------------------

def route_from_supervisor(state: AgentState) -> str:
    status = state.get("status", "working")

    if status in ("done", "error", "permission_denied"):
        return "audit_log"
    if state.get("iteration", 0) >= MAX_ITERATIONS:
        return "audit_log"

    current = state.get("current_agent", "")
    if current in ("backend", "devops", "qa"):
        return "human_approval"   # always pass through approval gate

    return "audit_log"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_secure_graph():
    graph = StateGraph(AgentState)

    # Security entry nodes (run once)
    graph.add_node("rbac_guard",        rbac_guard_node)
    graph.add_node("department_guard",  department_guard_node)
    graph.add_node("data_classifier",   data_classification_node)
    graph.add_node("intent_guard",           intent_guard_node)
    graph.add_node("prompt_injection_guard", prompt_injection_guard_node)

    # Multi-agent nodes
    graph.add_node("supervisor",      supervisor_node)
    graph.add_node("human_approval",  human_approval_node)
    graph.add_node("backend",         backend_node)
    graph.add_node("devops",          devops_node)
    graph.add_node("qa",              qa_node)

    # Audit exit node (run once)
    graph.add_node("audit_log",       audit_log_node)

    # ── Entry ──
    graph.set_entry_point("rbac_guard")

    # ── RBAC → dept_guard or block ──
    graph.add_conditional_edges(
        "rbac_guard",
        route_after_rbac,
        {"data_classifier": "department_guard", "audit_log": "audit_log"},
    )

    # ── Dept guard → classifier or block ──
    graph.add_conditional_edges(
        "department_guard",
        lambda s: "audit_log" if s.get("status") == "permission_denied" else "data_classifier",
        {"data_classifier": "data_classifier", "audit_log": "audit_log"},
    )

    # ── Classifier → intent_guard → supervisor ──
    graph.add_edge("data_classifier", "intent_guard")
    graph.add_conditional_edges(
        "intent_guard",
        lambda s: "audit_log" if s.get("status") == "permission_denied" else "prompt_injection_guard",
        {"prompt_injection_guard": "prompt_injection_guard", "audit_log": "audit_log"},
    )

    graph.add_conditional_edges(
        "prompt_injection_guard",
        lambda s: "audit_log" if s.get("status") == "permission_denied" else "supervisor",
        {"supervisor": "supervisor", "audit_log": "audit_log"},
    )

    # ── Supervisor → human_approval (always, except done) ──
    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "human_approval": "human_approval",
            "audit_log":      "audit_log",
        },
    )

    # ── human_approval → agent or audit_log (if rejected) ──
    graph.add_conditional_edges(
        "human_approval",
        lambda s: "audit_log" if s.get("status") == "permission_denied"
                  else s.get("current_agent", "audit_log"),
        {"backend": "backend", "devops": "devops", "qa": "qa", "audit_log": "audit_log"},
    )

    # ── Agents loop back to supervisor ──
    graph.add_edge("backend", "supervisor")
    graph.add_edge("devops",  "supervisor")
    graph.add_edge("qa",      "supervisor")

    # ── Audit → END ──
    graph.add_edge("audit_log", END)

    checkpoint_backend = os.getenv("CHECKPOINT_BACKEND", "sqlite")

    if checkpoint_backend == "memory":
        checkpointer = MemorySaver()
    else:
        db_path = os.getenv("CHECKPOINT_DB", "checkpoints.db")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        checkpointer = SqliteSaver(conn)

    return graph.compile(checkpointer=checkpointer)
