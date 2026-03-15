"""
Prompt Injection Guard

Scans user input for injection patterns before it reaches the supervisor LLM.
Deterministic regex — no LLM involved.

Sits between intent_guard and supervisor.
"""

import re
from langchain_core.messages import AIMessage, HumanMessage
from graph.state import AgentState

# Patterns that indicate prompt injection attempts
_INJECTION_PATTERNS: list[tuple[str, str]] = [
    # Classic instruction override
    (r"ignore\s+(all\s+)?(previous|above|prior|earlier)\s+instructions?", "instruction override"),
    (r"forget\s+(your\s+|the\s+|all\s+)?(role|instructions?|context|rules?|system)", "context wipe"),
    (r"disregard\s+(all\s+)?(previous|above|prior)\s+", "instruction override"),

    # System tag injection (must come before role hijack to avoid mis-labelling)
    (r"###\s*system", "system tag injection"),

    # Role hijack
    (r"you\s+are\s+now\s+", "role hijack"),
    (r"act\s+as\s+(if\s+)?(you\s+are\s+)?a\s+", "role hijack"),
    (r"pretend\s+(you\s+are|to\s+be)\s+", "role hijack"),
    (r"from\s+now\s+on\s+(you\s+are|act\s+as)", "role hijack"),
    (r"your\s+new\s+(role|persona|identity)\s+is", "role hijack"),

    # Jailbreak modes
    (r"\bDAN\s+mode\b", "jailbreak"),
    (r"developer\s+mode\s+(enabled|on|activated)", "jailbreak"),
    (r"jailbreak", "jailbreak"),
    (r"bypass\s+(your\s+)?(safety|filter|restriction|guideline)", "jailbreak"),

    # Template / delimiter injection
    (r"<\|im_start\|>", "delimiter injection"),
    (r"<\|im_end\|>",   "delimiter injection"),
    (r"\[\[.*?\]\]",    "template injection"),
    (r"\{\{.*?\}\}",    "template injection"),
    (r"<system>",       "system tag injection"),

    # Leakage attempts
    (r"(print|show|reveal|repeat|output)\s+(your\s+)?(system\s+prompt|instructions?|rules?)", "prompt leak"),
    (r"what\s+(are\s+your\s+|is\s+your\s+)(system\s+prompt|instructions?|rules?)", "prompt leak"),
    (r"what\s+are\s+your\s+system\s+", "prompt leak"),
]

_COMPILED = [(re.compile(p, re.IGNORECASE | re.DOTALL), label) for p, label in _INJECTION_PATTERNS]


def _extract_user_text(state: AgentState) -> str:
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            return msg.content if isinstance(msg.content, str) else str(msg.content)
    return state.get("user_goal", "")


def prompt_injection_guard_node(state: AgentState) -> AgentState:
    """Scan latest user message for injection patterns. Block if found."""
    text = _extract_user_text(state)

    for pattern, label in _COMPILED:
        if pattern.search(text):
            msg = AIMessage(
                content=(
                    f"Request blocked: prompt injection detected ({label}). "
                    f"Please rephrase your request."
                )
            )
            return {
                **state,
                "messages": [msg],
                "status":   "permission_denied",
                "error":    f"prompt_injection:{label}",
            }

    return state
