"""
Node 1.5: Department Guard

Runs after rbac_guard, before data_classifier.

Takes role-level allowed_tools and clearance_level already set in state,
then intersects them with the user's department policy:

  effective_tools     = role.allowed_tools ∩ dept.permitted_tools
  effective_clearance = min(role.clearance_ceiling, dept.max_clearance)

This lets an admin in the QA dept be capped at INTERNAL clearance
and only see test/log tools — not infra/write tools.
"""

from langchain_core.messages import AIMessage
from security.rbac import get_department_policy, effective_tools, effective_clearance
from graph.state import AgentState


def department_guard_node(state: AgentState) -> AgentState:
    department = state.get("user_department", "all")
    role = state.get("user_role", "")

    try:
        get_department_policy(department)   # validate dept exists
    except PermissionError as exc:
        msg = AIMessage(content=str(exc))
        return {
            **state,
            "messages": [msg],
            "status": "permission_denied",
            "error": str(exc),
            "allowed_tools": [],
        }

    final_tools = sorted(effective_tools(role, department))
    final_clearance = effective_clearance(role, department)

    return {
        **state,
        "allowed_tools":   final_tools,
        "clearance_level": final_clearance,
        "user_department": department,
    }
