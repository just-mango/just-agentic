"""
RBAC — Role-Based Access Control
Defines roles, clearance ceilings, and which tools each role may call.
"""

from dataclasses import dataclass, field
from typing import FrozenSet

# ---------------------------------------------------------------------------
# Data classification levels
# ---------------------------------------------------------------------------
class Clearance:
    PUBLIC       = 1
    INTERNAL     = 2
    CONFIDENTIAL = 3
    SECRET       = 4

    LABELS = {1: "PUBLIC", 2: "INTERNAL", 3: "CONFIDENTIAL", 4: "SECRET"}

    @classmethod
    def label(cls, level: int) -> str:
        return cls.LABELS.get(level, f"UNKNOWN({level})")


# ---------------------------------------------------------------------------
# Role definitions
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RolePolicy:
    name: str
    clearance_ceiling: int          # max data level this role can see
    allowed_tools: FrozenSet[str]   # exact tool names the LLM may call
    can_write: bool = False         # shorthand guard for write operations


_READ_TOOLS: FrozenSet[str] = frozenset({
    "read_file", "list_files", "search_code", "read_log",
    "git_status", "get_env", "web_search",
})

_ANALYZE_TOOLS: FrozenSet[str] = _READ_TOOLS | frozenset({
    "run_shell", "execute_python", "run_tests",
})

_WRITE_TOOLS: FrozenSet[str] = _ANALYZE_TOOLS | frozenset({
    "write_file",
})

ROLES: dict[str, RolePolicy] = {
    "viewer": RolePolicy(
        name="viewer",
        clearance_ceiling=Clearance.PUBLIC,
        allowed_tools=frozenset({"read_file", "list_files", "web_search"}),
    ),
    "analyst": RolePolicy(
        name="analyst",
        clearance_ceiling=Clearance.INTERNAL,
        allowed_tools=_READ_TOOLS,
    ),
    "manager": RolePolicy(
        name="manager",
        clearance_ceiling=Clearance.CONFIDENTIAL,
        allowed_tools=_ANALYZE_TOOLS,
        can_write=False,
    ),
    "admin": RolePolicy(
        name="admin",
        clearance_ceiling=Clearance.SECRET,
        allowed_tools=_WRITE_TOOLS,
        can_write=True,
    ),
}


# ---------------------------------------------------------------------------
# Department definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DepartmentPolicy:
    name: str
    permitted_tools: FrozenSet[str]   # tools relevant to this dept
    max_clearance: int                 # dept ceiling — can only reduce role clearance


DEPARTMENTS: dict[str, DepartmentPolicy] = {
    "engineering": DepartmentPolicy(
        name="engineering",
        permitted_tools=frozenset({
            "read_file", "write_file", "list_files", "search_code",
            "run_shell", "git_status", "execute_python", "run_tests", "web_search",
        }),
        max_clearance=Clearance.CONFIDENTIAL,
    ),
    "devops": DepartmentPolicy(
        name="devops",
        permitted_tools=frozenset({
            "read_file", "write_file", "list_files", "read_log",
            "run_shell", "git_status", "get_env", "web_search",
        }),
        max_clearance=Clearance.CONFIDENTIAL,
    ),
    "qa": DepartmentPolicy(
        name="qa",
        permitted_tools=frozenset({
            "read_file", "list_files", "search_code", "read_log",
            "run_shell", "run_tests", "execute_python", "web_search",
        }),
        max_clearance=Clearance.INTERNAL,
    ),
    "data": DepartmentPolicy(
        name="data",
        permitted_tools=frozenset({
            "read_file", "list_files", "search_code", "read_log",
            "execute_python", "web_search",
        }),
        max_clearance=Clearance.SECRET,
    ),
    "security": DepartmentPolicy(
        name="security",
        permitted_tools=_WRITE_TOOLS,
        max_clearance=Clearance.SECRET,
    ),
    "all": DepartmentPolicy(
        name="all",
        permitted_tools=_WRITE_TOOLS,  # no dept restriction — role decides
        max_clearance=Clearance.SECRET,
    ),
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_policy(role: str) -> RolePolicy:
    policy = ROLES.get(role)
    if policy is None:
        raise PermissionError(f"Unknown role: '{role}'. Allowed: {list(ROLES)}")
    return policy


def get_department_policy(department: str) -> DepartmentPolicy:
    policy = DEPARTMENTS.get(department)
    if policy is None:
        raise PermissionError(
            f"Unknown department: '{department}'. Allowed: {list(DEPARTMENTS)}"
        )
    return policy


def effective_tools(role: str, department: str) -> FrozenSet[str]:
    """role.allowed_tools ∩ dept.permitted_tools"""
    return get_policy(role).allowed_tools & get_department_policy(department).permitted_tools


def effective_clearance(role: str, department: str) -> int:
    """min(role.clearance_ceiling, dept.max_clearance)"""
    return min(
        get_policy(role).clearance_ceiling,
        get_department_policy(department).max_clearance,
    )


def is_tool_allowed(role: str, tool_name: str) -> bool:
    """Check role-level tool permission (without dept context)."""
    try:
        return tool_name in get_policy(role).allowed_tools
    except PermissionError:
        return False
