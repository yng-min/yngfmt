"""
Tests for supported formatter rules.
"""

from textwrap import dedent

from yngfmt.formatter import format_code


def test_formats_quotes_and_dictionary_spacing() -> None:
    source: str = "data={'name':'test','enabled':True}\nvalue=data[\"name\"]\n"

    assert format_code(source) == (
        'data = { "name": "test", "enabled": True }\n'
        "value = data['name']\n"
    )


def test_keeps_empty_dictionary_compact() -> None:
    assert format_code("data = { }\n") == "data = {}\n"


def test_does_not_add_spaces_to_multiline_dictionary() -> None:
    source: str = dedent(
        """
        data = {
            "name": "test",
            "enabled": True,
        }
        """
    ).lstrip()

    assert format_code(source) == source


def test_uses_double_quotes_outside_dictionary_key_access() -> None:
    source: str = "message = 'hello'\nitems = {'first': 'value'}\n"

    assert format_code(source) == (
        'message = "hello"\n'
        'items = { "first": "value" }\n'
    )


def test_preserves_bytes_and_prefixed_strings() -> None:
    source: str = "payload = b'abc'\npattern = r'\\d+'\n"

    assert format_code(source) == 'payload = b"abc"\npattern = r"\\d+"\n'


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


def test_never_wraps_code_by_line_length() -> None:
    source: str = (
        'result = service.process(first="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", '
        'second="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", '
        'third="cccccccccccccccccccccccccccccccccccccccc")\n'
    )

    assert len(source.rstrip("\n")) > 88
    assert format_code(source) == source


def test_is_idempotent() -> None:
    source: str = "data={'name':'test'}\nvalue=data[\"name\"]\n"
    formatted_source: str = format_code(source)

    assert format_code(formatted_source) == formatted_source
