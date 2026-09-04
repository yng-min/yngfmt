"""
Regression tests for the shared structural and density layout policy.
"""

from yngfmt.formatter import format_code


def test_compacts_simple_positional_and_keyword_arguments() -> None:
    source: str = """process(
    first,
    second,
    enabled=True,
)
"""
    assert format_code(source) == "process(first, second, enabled=True)\n"


def test_compacts_flat_expression_arguments_without_nested_structure() -> None:
    source: str = """process(
    first + second + third + fourth,
    lower <= value < upper,
)
"""
    assert format_code(source) == "process(first + second + third + fourth, lower <= value < upper)\n"


def test_compacts_outer_call_around_sparse_nested_call() -> None:
    source: str = """process(
    first,
    build_value(
        enabled=True,
        timeout=10,
    ),
)
"""
    assert format_code(source) == "process(first, build_value(enabled=True, timeout=10))\n"


def test_compacts_outer_call_around_sparse_nested_collection() -> None:
    source: str = """process(
    first,
    {
        "enabled": True,
        "timeout": 10,
    },
)
"""
    assert format_code(source) == "process(first, { \"enabled\": True, \"timeout\": 10 })\n"


def test_preserves_comment_bearing_container_shape() -> None:
    source: str = """process(
    first,
    # Preserve why this value is special.
    second,
)
"""
    assert format_code(source) == source


def test_expands_five_named_arguments() -> None:
    source: str = "process(alpha=1, beta=2, gamma=3, delta=4, epsilon=5)\n"
    assert format_code(source) == """process(
    alpha=1,
    beta=2,
    gamma=3,
    delta=4,
    epsilon=5,
)
"""


def test_keeps_six_short_positional_arguments_compact() -> None:
    source: str = """process(
    a,
    b,
    c,
    d,
    e,
    f,
)
"""
    assert format_code(source) == "process(a, b, c, d, e, f)\n"


def test_expands_majority_long_named_arguments() -> None:
    source: str = (
        "process(first_descriptive_parameter=value, "
        "second_descriptive_parameter=value, "
        "third_descriptive_parameter=value)\n"
    )
    assert format_code(source) == """process(
    first_descriptive_parameter=value,
    second_descriptive_parameter=value,
    third_descriptive_parameter=value,
)
"""


def test_keeps_single_long_named_outlier_compact() -> None:
    source: str = (
        "process(first_descriptive_parameter=value, "
        "second=value, "
        "third=value)\n"
    )
    assert format_code(source) == source


def test_keeps_one_long_string_compact() -> None:
    value: str = "x" * 120
    source: str = f'process("{value}")\n'
    assert format_code(source) == source


def test_keeps_two_long_string_values_compact_below_soft_ceiling() -> None:
    first: str = "a" * 40
    second: str = "b" * 40
    source: str = f'process("{first}", "{second}")\n'
    assert format_code(source) == source


def test_expands_majority_long_values_across_three_items() -> None:
    first: str = "a" * 40
    second: str = "b" * 40
    source: str = f'process("{first}", "{second}", "short")\n'
    assert format_code(source) == f"""process(
    "{first}",
    "{second}",
    "short",
)
"""


def test_expands_compact_form_above_soft_ceiling() -> None:
    value: str = "x" * 190
    source: str = f'result = process("{value}")\n'
    assert format_code(source) == f"""result = process(
    "{value}",
)
"""


def test_compacts_homogeneous_run_when_nested_children_are_sparse() -> None:
    source: str = """self.assertIn("first", output)
self.assertEqual(
    actual,
    build_expected(
        enabled=True,
        timeout=10,
    ),
)
self.assertIn("second", output)
"""
    assert format_code(source) == """self.assertIn("first", output)
self.assertEqual(actual, build_expected(enabled=True, timeout=10))
self.assertIn("second", output)
"""


def test_compacts_soft_density_outlier_inside_exact_callee_cohort() -> None:
    source: str = """parser.add_argument("--first", help="Short help.")
parser.add_argument(
    "--second",
    default=str(
        default_cache_path(),
    ),
    help="A somewhat longer help string that makes this call dense in isolation.",
)
parser.add_argument("--third", help="Short help.")
"""
    assert format_code(source) == """parser.add_argument("--first", help="Short help.")
parser.add_argument("--second", default=str(default_cache_path()), help="A somewhat longer help string that makes this call dense in isolation.")
parser.add_argument("--third", help="Short help.")
"""


def test_keeps_hard_structural_outlier_inside_exact_callee_cohort() -> None:
    source: str = """parser.add_argument("--first", help="Short help.")
parser.add_argument(
    "--second",
    default=build_value(
        alpha=1,
        beta=2,
        gamma=3,
        delta=4,
        epsilon=5,
    ),
)
parser.add_argument("--third", help="Short help.")
"""
    assert format_code(source) == """parser.add_argument("--first", help="Short help.")
parser.add_argument(
    "--second",
    default=build_value(
        alpha=1,
        beta=2,
        gamma=3,
        delta=4,
        epsilon=5,
    ),
)
parser.add_argument("--third", help="Short help.")
"""


def test_compacts_realistic_argparse_registration_block() -> None:
    source: str = """snapshot_parser.add_argument("--device-id", required=True, help="Opaque Meloft device identifier.")
snapshot_parser.add_argument("--owner-user-id", help="Optional opaque Meloft user identifier.")
snapshot_parser.add_argument("--device-label", help="Optional local device label.")
snapshot_parser.add_argument(
    "--fl-studio-version",
    help="Override Windows auto-discovery with one known FL Studio version.",
)
snapshot_parser.add_argument(
    "--inventory-cache",
    default=str(
        default_capability_inventory_cache_path(),
    ),
    help="Local metadata inventory cache path.",
)
snapshot_parser.add_argument(
    "--no-inventory-cache",
    action="store_true",
    help="Disable persistent inventory cache reuse for this capture.",
)
snapshot_parser.add_argument(
    "--force",
    action="store_true",
    help="Bypass a fresh metadata cache and complete a new inventory scan.",
)
snapshot_parser.add_argument(
    "--plugin-root",
    action="append",
    default=[],
    help="Custom plugin root to scan for every supported format. May be specified multiple times.",
)
"""
    expected: str = """snapshot_parser.add_argument("--device-id", required=True, help="Opaque Meloft device identifier.")
snapshot_parser.add_argument("--owner-user-id", help="Optional opaque Meloft user identifier.")
snapshot_parser.add_argument("--device-label", help="Optional local device label.")
snapshot_parser.add_argument("--fl-studio-version", help="Override Windows auto-discovery with one known FL Studio version.")
snapshot_parser.add_argument("--inventory-cache", default=str(default_capability_inventory_cache_path()), help="Local metadata inventory cache path.")
snapshot_parser.add_argument("--no-inventory-cache", action="store_true", help="Disable persistent inventory cache reuse for this capture.")
snapshot_parser.add_argument("--force", action="store_true", help="Bypass a fresh metadata cache and complete a new inventory scan.")
snapshot_parser.add_argument("--plugin-root", action="append", default=[], help="Custom plugin root to scan for every supported format. May be specified multiple times.")
"""
    formatted: str = format_code(source)
    assert formatted == expected
    assert format_code(formatted) == formatted


def test_applies_named_density_to_function_definition() -> None:
    source: str = "def execute(alpha: str, beta: str, gamma: str, delta: str, epsilon: str) -> None:\n    pass\n"
    assert format_code(source) == """def execute(
    alpha: str,
    beta: str,
    gamma: str,
    delta: str,
    epsilon: str,
) -> None:
    pass
"""


def test_compacts_sparse_function_definition() -> None:
    source: str = """def execute(
    first: str,
    second: str,
) -> None:
    pass
"""
    assert format_code(source) == """def execute(first: str, second: str) -> None:
    pass
"""


def test_preserves_parameter_separators_when_compacting() -> None:
    source: str = """def execute(
    first: str,
    /,
    second: str = "value",
    *,
    enabled: bool = True,
) -> None:
    pass
"""
    assert format_code(source) == """def execute(first: str, /, second: str = "value", *, enabled: bool = True) -> None:
    pass
"""


def test_preserves_grouping_for_starred_conditional_call_argument() -> None:
    source: str = "process(*((first,) if enabled else ()))\n"
    expected: str = """process(
    *((first,) if enabled else ()),
)
"""
    formatted: str = format_code(source)
    assert formatted == expected
    assert format_code(formatted) == formatted


def test_preserves_grouping_for_starred_conditional_tuple_item() -> None:
    source: str = "values = (first, *((second,) if enabled else ()), third)\n"
    expected: str = """values = (
    first,
    *((second,) if enabled else ()),
    third,
)
"""
    formatted: str = format_code(source)
    assert formatted == expected
    assert format_code(formatted) == formatted


def test_preserves_grouping_for_double_starred_conditional_call_argument() -> None:
    source: str = "process(**({\"enabled\": True} if condition else {}))\n"
    expected: str = """process(
    **({ "enabled": True } if condition else {}),
)
"""
    formatted: str = format_code(source)
    assert formatted == expected
    assert format_code(formatted) == formatted


def test_preserves_grouping_for_double_starred_conditional_dictionary_item() -> None:
    source: str = "payload = {\"value\": 1, **({\"enabled\": True} if condition else {})}\n"
    expected: str = """payload = {
    "value": 1,
    **({ "enabled": True } if condition else {}),
}
"""
    formatted: str = format_code(source)
    assert formatted == expected
    assert format_code(formatted) == formatted


def test_reaches_fixed_point_for_multiline_double_starred_conditional_dictionary_item() -> None:
    source: str = """payload = {
    "data": {
        **(
            { "production_freeze": build() }
            if enabled
            else {}
        ),
    },
}
"""
    formatted: str = format_code(source)
    assert format_code(formatted) == formatted


def test_expands_five_dictionary_entries() -> None:
    source: str = "payload = { \"a\": 1, \"b\": 2, \"c\": 3, \"d\": 4, \"e\": 5 }\n"
    assert format_code(source) == """payload = {
    "a": 1,
    "b": 2,
    "c": 3,
    "d": 4,
    "e": 5,
}
"""


def test_compacts_six_short_sequence_items() -> None:
    source: str = """values = [
    1,
    2,
    3,
    4,
    5,
    6,
]
"""
    assert format_code(source) == "values = [1, 2, 3, 4, 5, 6]\n"


def test_is_idempotent_for_nested_layout() -> None:
    source: str = """process(
    first,
    build_value(
        enabled=True,
        timeout=10,
    ),
)
"""
    formatted: str = format_code(source)
    assert formatted == "process(first, build_value(enabled=True, timeout=10))\n"
    assert format_code(formatted) == formatted
