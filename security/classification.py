"""
Data Classification
Each DataChunk carries a classification level.
filter_by_clearance() strips chunks the user is not cleared for.
"""

from dataclasses import dataclass
from typing import Any

from security.rbac import Clearance


@dataclass
class DataChunk:
    content: Any
    classification: int          # use Clearance.* constants
    source: str = ""             # optional: where this data came from

    def label(self) -> str:
        return Clearance.label(self.classification)

    def is_visible_to(self, clearance_level: int) -> bool:
        return self.classification <= clearance_level


def filter_by_clearance(
    chunks: list[DataChunk],
    clearance_level: int,
) -> tuple[list[DataChunk], list[int]]:
    """
    Returns:
        visible: chunks the user may see
        stripped_levels: classification levels of chunks that were removed
    """
    visible: list[DataChunk] = []
    stripped_levels: list[int] = []

    for chunk in chunks:
        if chunk.is_visible_to(clearance_level):
            visible.append(chunk)
        else:
            stripped_levels.append(chunk.classification)

    return visible, stripped_levels


def chunks_to_context_text(chunks: list[DataChunk]) -> str:
    """Flatten visible chunks into a single context string for the LLM."""
    if not chunks:
        return ""
    parts = []
    for chunk in chunks:
        parts.append(f"[{chunk.label()} | {chunk.source}]\n{chunk.content}")
    return "\n\n---\n\n".join(parts)
