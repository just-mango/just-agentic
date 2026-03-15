"""
Node 1: RBAC Guard

Two auth modes:
  - JWT mode  : state["jwt_token"] is set → decode and validate token
  - Dev mode  : use state["user_id"] / ["user_role"] / ["user_department"] directly

Populates: user_id, user_role, user_department, clearance_level, allowed_tools
Blocks unknown roles / invalid tokens with status = permission_denied.
"""

from langchain_core.messages import AIMessage
from security.rbac import get_policy
from graph.state import AgentState


def rbac_guard_node(state: AgentState) -> AgentState:
    jwt_token = state.get("jwt_token", "")

    if jwt_token:
        return _auth_via_token(state, jwt_token)
    return _auth_via_plain(state)


# ── JWT path ──────────────────────────────────────────────────────────────

def _auth_via_token(state: AgentState, token: str) -> AgentState:
    try:
        from security.jwt_auth import decode_token
        ctx = decode_token(token)
    except (ValueError, RuntimeError, PermissionError) as exc:
        return _deny(state, str(exc))

    return {
        **state,
        "user_id":         ctx.user_id,
        "user_role":       ctx.role,
        "user_department": ctx.department,
        "clearance_level": ctx.clearance_level,
        "allowed_tools":   _role_tools(ctx.role),
        "status":          "ok",
    }


# ── Plain credentials path (dev / testing) ────────────────────────────────

def _auth_via_plain(state: AgentState) -> AgentState:
    user_id = state.get("user_id", "anonymous")
    role    = state.get("user_role", "")

    try:
        policy = get_policy(role)
    except PermissionError as exc:
        return _deny(state, str(exc))

    return {
        **state,
        "user_id":         user_id,
        "user_role":       role,
        "user_department": state.get("user_department", "all"),
        "clearance_level": policy.clearance_ceiling,
        "allowed_tools":   list(policy.allowed_tools),
        "status":          "ok",
    }


# ── Helpers ───────────────────────────────────────────────────────────────

def _role_tools(role: str) -> list[str]:
    return list(get_policy(role).allowed_tools)


def _deny(state: AgentState, reason: str) -> AgentState:
    return {
        **state,
        "messages":    [AIMessage(content=f"Authentication failed: {reason}")],
        "status":      "permission_denied",
        "error":       reason,
        "allowed_tools": [],
    }
