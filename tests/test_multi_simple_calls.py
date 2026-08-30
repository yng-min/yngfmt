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


def test_compacts_flat_expression_arguments_without_nested_structure() -> None:
    source: str = '''process(
    first + second + third + fourth,
    lower <= value < upper,
)
'''
    assert format_code(source) == "process(first + second + third + fourth, lower <= value < upper)\n"


def test_keeps_call_inside_flat_expression_multiline() -> None:
    source: str = '''process(
    build_value() + fallback,
    second,
)
'''
    assert format_code(source) == source


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


def test_compacts_short_complex_call_inside_homogeneous_assert_run() -> None:
    source: str = '''self.assertIn("first", output)
self.assertEqual(
    actual,
    build_expected(
        enabled=True,
        timeout=10,
    ),
)
self.assertIn("second", output)
'''
    assert format_code(source) == '''self.assertIn("first", output)
self.assertEqual(actual, build_expected(enabled=True, timeout=10))
self.assertIn("second", output)
'''


def test_keeps_over_limit_complex_call_inside_homogeneous_assert_run() -> None:
    long_value: str = "x" * 190
    source: str = f'''self.assertIn("first", output)
self.assertEqual(
    actual,
    build_expected(
        value="{long_value}",
    ),
)
self.assertIn("second", output)
'''
    assert format_code(source) == source


def test_different_method_family_breaks_homogeneous_run() -> None:
    source: str = '''self.assertIn("first", output)
self.checkValue(
    actual,
    build_expected(
        enabled=True,
        timeout=10,
    ),
)
'''
    assert format_code(source) == source


def test_same_receiver_and_snake_case_family_form_homogeneous_run() -> None:
    source: str = '''client.get_value(first)
client.get_other(
    actual,
    build_expected(
        enabled=True,
    ),
)
'''
    assert format_code(source) == '''client.get_value(first)
client.get_other(actual, build_expected(enabled=True))
'''
