"""
Regression tests for structure-aware layout normalization.
"""

from yngfmt.formatter import format_code


def test_collapses_single_item_list_around_implicit_string_concatenation() -> None:
    source: str = '''sections: list[str] = [
    (
        "A pending Python edit was blocked before execution. "
        "Regenerate the edit while actively applying the style contract."
    )
]
'''
    assert format_code(source) == '''sections: list[str] = [(
    "A pending Python edit was blocked before execution. "
    "Regenerate the edit while actively applying the style contract."
)]
'''


def test_preserves_single_item_list_around_multiline_string_literal() -> None:
    source: str = '''values = [
    """first
    second"""
]
'''
    assert format_code(source) == source
