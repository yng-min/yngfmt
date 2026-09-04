"""
Regression tests for the shared structural and density layout policy.
"""

from pathlib import Path

from yngfmt.formatter import format_code


_FIXTURES = Path(__file__).parent / "fixtures"


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


def test_compacts_call_containing_canonically_compact_nested_expression() -> None:
    source: str = "process(first, build_value(enabled=True, timeout=10))\n"
    assert format_code(source) == source


def test_compacts_call_containing_canonically_compact_collection() -> None:
    source: str = "process(first, { \"enabled\": True, \"timeout\": 10 })\n"
    assert format_code(source) == source


def test_expands_parent_only_when_nested_child_is_canonically_expanded() -> None:
    source: str = "process(first, build_value(alpha=1, beta=2, gamma=3, delta=4, epsilon=5))\n"
    assert format_code(source) == '''process(
    first,
    build_value(
        alpha=1,
        beta=2,
        gamma=3,
        delta=4,
        epsilon=5,
    ),
)
'''


def test_preserves_comment_bearing_container_shape() -> None:
    source: str = '''process(
    first,
    # Preserve why this value is special.
    second,
)
'''
    assert format_code(source) == source


def test_expands_five_named_arguments() -> None:
    source: str = "process(alpha=1, beta=2, gamma=3, delta=4, epsilon=5)\n"
    assert format_code(source) == '''process(
    alpha=1,
    beta=2,
    gamma=3,
    delta=4,
    epsilon=5,
)
'''


def test_keeps_six_short_positional_arguments_compact() -> None:
    source: str = '''process(
    a,
    b,
    c,
    d,
    e,
    f,
)
'''
    assert format_code(source) == "process(a, b, c, d, e, f)\n"


def test_expands_three_long_named_arguments() -> None:
    source: str = (
        "process(first_descriptive_parameter=value, "
        "second_descriptive_parameter=value, "
        "third_descriptive_parameter=value)\n"
    )
    assert format_code(source) == '''process(
    first_descriptive_parameter=value,
    second_descriptive_parameter=value,
    third_descriptive_parameter=value,
)
'''


def test_keeps_one_long_string_compact() -> None:
    value: str = "x" * 120
    source: str = f'process("{value}")\n'
    assert format_code(source) == source


def test_keeps_one_long_named_item_compact() -> None:
    source: str = "parser.add_argument(\"--fl-studio-version\", help=\"Override Windows auto-discovery with one known FL Studio version.\")\n"
    assert format_code(source) == source


def test_keeps_one_long_name_compact() -> None:
    source: str = "process(extraordinarily_long_parameter_name=value, short=1)\n"
    assert format_code(source) == source


def test_expands_multiple_long_string_values() -> None:
    first: str = "a" * 40
    second: str = "b" * 40
    source: str = f'process("{first}", "{second}")\n'
    assert format_code(source) == f'''process(
    "{first}",
    "{second}",
)
'''


def test_expands_compact_form_above_soft_ceiling() -> None:
    value: str = "x" * 190
    source: str = f'result = process("{value}")\n'
    assert format_code(source) == f'''result = process(
    "{value}",
)
'''


def test_unrelated_call_run_does_not_override_recursive_layout() -> None:
    source: str = '''self.assertIn("first", output)
self.assertEqual(actual, build_expected(enabled=True, timeout=10))
self.assertIn("second", output)
'''
    assert format_code(source) == source


def test_same_callee_cohort_only_promotes_compact_calls() -> None:
    source: str = '''parser.add_argument("--short", help="Short help.")
parser.add_argument("--dense", alpha=1, beta=2, gamma=3, delta=4, epsilon=5)
'''
    assert format_code(source) == '''parser.add_argument(
    "--short",
    help="Short help.",
)
parser.add_argument(
    "--dense",
    alpha=1,
    beta=2,
    gamma=3,
    delta=4,
    epsilon=5,
)
'''


def test_formats_meloft_argparse_registration_fixture_consistently() -> None:
    source: str = (_FIXTURES / "meloft_argparse.input.txt").read_text(encoding="utf-8")
    expected: str = (_FIXTURES / "meloft_argparse.expected.txt").read_text(encoding="utf-8")
    formatted: str = format_code(source)
    assert formatted == expected
    assert format_code(formatted) == formatted


def test_applies_named_density_to_function_definition() -> None:
    source: str = "def execute(alpha: str, beta: str, gamma: str, delta: str, epsilon: str) -> None:\n    pass\n"
    assert format_code(source) == '''def execute(
    alpha: str,
    beta: str,
    gamma: str,
    delta: str,
    epsilon: str,
) -> None:
    pass
'''


def test_compacts_sparse_function_definition() -> None:
    source: str = '''def execute(
    first: str,
    second: str,
) -> None:
    pass
'''
    assert format_code(source) == '''def execute(first: str, second: str) -> None:
    pass
'''


def test_preserves_parameter_separators_when_compacting() -> None:
    source: str = '''def execute(
    first: str,
    /,
    second: str = "value",
    *,
    enabled: bool = True,
) -> None:
    pass
'''
    assert format_code(source) == '''def execute(first: str, /, second: str = "value", *, enabled: bool = True) -> None:
    pass
'''


def test_preserves_grouping_for_starred_conditional_call_argument() -> None:
    source: str = "process(*((first,) if enabled else ()))\n"
    expected: str = '''process(
    *((first,) if enabled else ()),
)
'''
    formatted: str = format_code(source)
    assert formatted == expected
    assert format_code(formatted) == formatted


def test_preserves_grouping_for_starred_conditional_tuple_item() -> None:
    source: str = "values = (first, *((second,) if enabled else ()), third)\n"
    expected: str = '''values = (
    first,
    *((second,) if enabled else ()),
    third,
)
'''
    formatted: str = format_code(source)
    assert formatted == expected
    assert format_code(formatted) == formatted


def test_preserves_grouping_for_double_starred_conditional_call_argument() -> None:
    source: str = "process(**({\"enabled\": True} if condition else {}))\n"
    expected: str = '''process(
    **({ "enabled": True } if condition else {}),
)
'''
    formatted: str = format_code(source)
    assert formatted == expected
    assert format_code(formatted) == formatted


def test_preserves_grouping_for_double_starred_conditional_dictionary_item() -> None:
    source: str = "payload = {\"value\": 1, **({\"enabled\": True} if condition else {})}\n"
    expected: str = '''payload = {
    "value": 1,
    **({ "enabled": True } if condition else {}),
}
'''
    formatted: str = format_code(source)
    assert formatted == expected
    assert format_code(formatted) == formatted


def test_reaches_fixed_point_for_multiline_double_starred_conditional_dictionary_item() -> None:
    source: str = '''payload = {
    "data": {
        **(
            { "production_freeze": build() }
            if enabled
            else {}
        ),
    },
}
'''
    formatted: str = format_code(source)
    assert formatted == '''payload = {
    "data": {
        **({ "production_freeze": build() }
        if enabled
        else {}),
    },
}
'''
    assert format_code(formatted) == formatted


def test_expands_five_dictionary_entries() -> None:
    source: str = "payload = { \"a\": 1, \"b\": 2, \"c\": 3, \"d\": 4, \"e\": 5 }\n"
    assert format_code(source) == '''payload = {
    "a": 1,
    "b": 2,
    "c": 3,
    "d": 4,
    "e": 5,
}
'''


def test_compacts_six_short_sequence_items() -> None:
    source: str = '''values = [
    1,
    2,
    3,
    4,
    5,
    6,
]
'''
    assert format_code(source) == "values = [1, 2, 3, 4, 5, 6]\n"


def test_is_idempotent_for_nested_layout() -> None:
    source: str = "process(first, build_value(enabled=True, timeout=10))\n"
    formatted: str = format_code(source)
    assert format_code(formatted) == formatted
