"""
Regression tests for compact multi-argument call layout.
"""

from yngfmt.formatter import format_code


def test_compacts_multiline_assertion_with_simple_arguments() -> None:
    source: str = '''self.assertEqual(
    comparison_process.returncode,
    0,
    comparison_process.stdout + comparison_process.stderr,
)
self.assertIn("maxAbsoluteDifference: 0", comparison_process.stdout)
'''
    assert format_code(source) == '''self.assertEqual(comparison_process.returncode, 0, comparison_process.stdout + comparison_process.stderr)
self.assertIn("maxAbsoluteDifference: 0", comparison_process.stdout)
'''


def test_compacts_simple_positional_and_keyword_arguments() -> None:
    source: str = '''process(
    first,
    second,
    enabled=True,
)
'''
    assert format_code(source) == "process(first, second, enabled=True)\n"


def test_keeps_nested_call_multiline() -> None:
    source: str = '''process(
    first,
    build_value(
        enabled=True,
        timeout=10,
    ),
)
'''
    assert format_code(source) == source


def test_keeps_collection_argument_multiline() -> None:
    source: str = '''process(
    first,
    {
        "enabled": True,
        "timeout": 10,
    },
)
'''
    assert format_code(source) == source


def test_keeps_comment_bearing_call_multiline() -> None:
    source: str = '''process(
    first,
    # Preserve why this value is special.
    second,
)
'''
    assert format_code(source) == source
