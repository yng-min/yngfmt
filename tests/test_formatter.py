"""
Tests for supported formatter rules.
"""

from textwrap import dedent

import pytest

from yngfmt import formatter

from yngfmt.formatter import format_code


def test_formats_quotes_and_dictionary_spacing() -> None:
    source: str = "data={'name':'test','enabled':True}\nvalue=data[\"name\"]\n"
    assert format_code(source) == (
        "data = { \"name\": \"test\", \"enabled\": True }\n"
        "value = data['name']\n"
    )


def test_keeps_empty_dictionary_compact() -> None:
    assert format_code("data = { }\n") == "data = {}\n"


def test_compacts_sparse_multiline_dictionary() -> None:
    source: str = dedent(
        """
        data = {
            "name": "test",
            "enabled": True,
        }
        """
    ).lstrip()
    assert format_code(source) == "data = { \"name\": \"test\", \"enabled\": True }\n"


def test_uses_double_quotes_outside_dictionary_key_access() -> None:
    source: str = "message = 'hello'\nitems = {'first': 'value'}\n"
    assert format_code(source) == (
        "message = \"hello\"\n"
        "items = { \"first\": \"value\" }\n"
    )


def test_preserves_bytes_and_prefixed_strings() -> None:
    source: str = "payload = b'abc'\npattern = r'\\d+'\n"
    assert format_code(source) == "payload = b\"abc\"\npattern = r\"\\d+\"\n"


def test_preserves_f_string_expression_quotes() -> None:
    source: str = "message = f\"fields: {', '.join(fields)}\"\n"
    assert format_code(source) == source


def test_preserves_triple_quoted_docstring() -> None:
    source: str = dedent(
        '''
        def load() -> None:
            """
            Load data.
            """
            return None
        '''
    ).lstrip()
    assert format_code(source) == source


def test_uses_one_space_before_inline_comment() -> None:
    source: str = "value = 1  # explanation\n"
    assert format_code(source) == "value = 1 # explanation\n"


def test_uses_one_space_before_inline_directive() -> None:
    source: str = "import plugin_b  # yngfmt: keep-imports\n"
    assert format_code(source) == "import plugin_b # yngfmt: keep-imports\n"


def test_applies_explicit_mechanical_whitespace_fixes() -> None:
    source: str = "value=process( 1,2 )\n"
    assert format_code(source) == "value = process(1, 2)\n"


def test_expands_multiple_long_named_values_by_density() -> None:
    source: str = (
        "result = service.process(first=\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\", "
        "second=\"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\", "
        "third=\"cccccccccccccccccccccccccccccccccccccccc\")\n"
    )
    assert len(source.rstrip("\n")) > 88
    assert format_code(source) == '''result = service.process(
    first="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    second="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    third="cccccccccccccccccccccccccccccccccccccccc",
)
'''


def test_keeps_one_long_positional_value_compact_below_soft_ceiling() -> None:
    long_value: str = "x" * 150
    source: str = f'process("{long_value}")\n'
    assert format_code(source) == source


def test_expands_outer_call_and_compacts_sparse_nested_dictionary() -> None:
    source: str = '''service.process(options={
    "enabled": True,
    "timeout": 10,
})
'''
    assert format_code(source) == '''service.process(
    options={ "enabled": True, "timeout": 10 },
)
'''


def test_compacts_simple_multiline_call_chain() -> None:
    source: str = '''for line in (session_directory / "blocks.jsonl").read_text(
    encoding="utf-8",
).splitlines():
    process(line)
'''
    assert format_code(source) == '''for line in (session_directory / "blocks.jsonl").read_text(encoding="utf-8").splitlines():
    process(line)
'''


def test_compacts_broken_attribute_call_chain() -> None:
    source: str = '''blocks = [
    line
    for line in (session_directory / "blocks.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
    if line.strip()
]
'''
    assert format_code(source) == '''blocks = [
    line
    for line in (session_directory / "blocks.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
'''


def test_expands_outer_call_around_compact_nested_call() -> None:
    source: str = '''diagnostics.extend(
    _validate_result_keys(
        keys=keys,
        node=node,
        path=path,
        config=config,
    )
)
'''
    assert format_code(source) == '''diagnostics.extend(
    _validate_result_keys(keys=keys, node=node, path=path, config=config),
)
'''


def test_expands_list_around_compact_nested_call() -> None:
    source: str = '''def build(path: str) -> list[object]:
    return [
        Diagnostic(
            path=path,
            code="YNG601",
        )
    ]
'''
    assert format_code(source) == '''def build(path: str) -> list[object]:
    return [
        Diagnostic(path=path, code="YNG601"),
    ]
'''


def test_preserves_generator_expression_call_layout() -> None:
    source: str = '''values = tuple(
    item
    for item in items
    if item.enabled
)
'''
    assert format_code(source) == source


def test_preserves_comment_and_expanded_nested_simple_call() -> None:
    source: str = '''service.process(
    # explain the argument
    create_value(
        enabled=True,
    ),
)
'''
    assert format_code(source) == '''service.process(
    # explain the argument
    create_value(enabled=True),
)
'''


def test_compacts_thin_straight_line_function_body() -> None:
    source: str = '''def check() -> None:
    value = build()

    assert value is not None
'''
    assert format_code(source) == '''def check() -> None:
    value = build()
    assert value is not None
'''


def test_preserves_type_ignore_when_compaction_moves_its_line() -> None:
    source: str = '''def execute() -> object:
    value = build()

    return value  # type: ignore[return-value]
'''
    assert format_code(source) == '''def execute() -> object:
    value = build()
    return value # type: ignore[return-value]
'''


def test_keeps_spacing_when_comment_marks_stage_boundary() -> None:
    source: str = '''def check() -> None:
    value = build()

    # Verify the result.
    assert value is not None
'''
    assert format_code(source) == source


def test_rejects_mechanical_rewrite_that_changes_ast(monkeypatch: pytest.MonkeyPatch) -> None:
    def change_value(source: str) -> str:
        return "value = 2\n"

    monkeypatch.setattr(formatter, "_format_mechanical_whitespace", change_value)
    with pytest.raises(ValueError, match="mechanical whitespace pass"):
        format_code("value = 1\n")


def test_rejects_custom_rewrite_that_changes_ast(monkeypatch: pytest.MonkeyPatch) -> None:
    def change_value(source: str) -> str:
        return "value = 2\n"

    monkeypatch.setattr(formatter, "apply_custom_transforms", change_value)
    with pytest.raises(ValueError, match="custom transform pass"):
        format_code("value = 1\n")


def test_is_idempotent() -> None:
    source: str = "data={'name':'test'}\nvalue=data[\"name\"]\n"
    formatted_source: str = format_code(source)
    assert format_code(formatted_source) == formatted_source
