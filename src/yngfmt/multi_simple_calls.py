"""
Backward-compatible entry point for canonical container layout.
"""

from yngfmt.layout_policy import normalize_layout


def compact_multi_simple_calls(source: str) -> str:
    """
    Normalize calls through the shared layout policy.
    """
    return normalize_layout(source=source)
