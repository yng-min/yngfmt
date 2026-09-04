"""
Tests for style guide linter rules.
"""

from pathlib import Path

from yngfmt.formatter import format_code

from yngfmt.linter import ResultConfig, lint_code


def _diagnostics(source: str, result_config: ResultConfig = ResultConfig()):
    return lint_code(source=source, path=Path("test.py"), result_config=result_config)


def _codes(source: str, result_config: ResultConfig = ResultConfig()) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in _diagnostics(source=source, result_config=result_config)
    ]


def test_accepts_core_style_rules() -> None:
    source = '''"""
Module description.
"""

from pathlib import Path
import json


class ExampleService:
    """
    Example service.
    """
    def get_value(self, data: dict[str, str]) -> str:
        enabled: bool = True
        value = data['name']
        return value if enabled else ""
'''.lstrip()
    assert _codes(source=source) == []


def test_reports_quote_and_key_access_rules() -> None:
    source = "message = 'hello'\nvalue = data[\"name\"]\n"
    assert _codes(source=source) == ["YNG101", "YNG103"]


def test_reports_docstring_delimiter_layout() -> None:
    source = '''"""Module description.
"""

def execute() -> None:
    """
    Execute."""
    return None
'''
    assert _codes(source=source) == ["YNG107", "YNG108"]


def test_reports_dictionary_spacing() -> None:
    source = "data = {\"name\": \"test\"}\n"
    assert _codes(source=source) == ["YNG109"]


def test_reports_simple_multiline_call() -> None:
    source = '''def execute(value: str) -> str:
    return process(
        value,
    )
'''
    assert _codes(source=source) == ["YNG701"]


def test_reports_noncanonical_multiline_simple_call_before_comma_detail() -> None:
    source = '''def execute(first: str, second: str) -> str:
    return process(
        first,
        second
    )
'''
    assert _codes(source=source) == ["YNG701"]


def test_reports_single_line_trailing_comma() -> None:
    source = '''def execute(value: str) -> str:
    return process(value,)
'''
    assert _codes(source=source) == ["YNG703"]


def test_reports_multiline_zero_argument_call() -> None:
    source = '''def execute() -> str:
    return process(
    )
'''
    assert _codes(source=source) == ["YNG704"]


def test_reports_noncanonical_nested_simple_call() -> None:
    source = '''def execute() -> str:
    return process(
        create_value(
            enabled=True,
            timeout=10,
        ),
    )
'''
    assert _codes(source=source) == ["YNG701"]


def test_reports_outer_comma_and_nested_dictionary_layout() -> None:
    source = '''def execute() -> object:
    return process(options={
        "enabled": True,
        "timeout": 10,
    })
'''
    assert _codes(source=source) == ["YNG702", "YNG705"]


def test_reports_only_nested_dictionary_layout_when_outer_comma_is_valid() -> None:
    source = '''def execute() -> object:
    return process(options={
        "enabled": True,
        "timeout": 10,
    },)
'''
    assert _codes(source=source) == ["YNG705"]


def test_reports_dense_call_that_must_expand() -> None:
    source = "process(alpha=1, beta=2, gamma=3, delta=4, epsilon=5)\n"
    assert _codes(source=source) == ["YNG705"]


def test_reports_sparse_function_definition_that_must_compact() -> None:
    source = '''def execute(
    first: str,
    second: str,
) -> None:
    return None
'''
    assert _codes(source=source) == ["YNG705"]


def test_reports_missing_dictionary_trailing_comma() -> None:
    source = '''payload = {
    "first_descriptive_key": first_descriptive_value,
    "second_descriptive_key": second_descriptive_value
}
'''
    assert _codes(source=source) == ["YNG706"]


def test_formatter_output_satisfies_shared_layout_linter() -> None:
    source = '''def execute(
    first: str,
    second: str,
) -> object:
    return process(first, build_value(enabled=True, timeout=10))
'''
    assert _codes(source=format_code(source)) == []


def test_reports_naming_and_type_annotation_rules() -> None:
    source = "class bad_name:\n    def GetValue(self, value):\n        return value\n"
    assert _codes(source=source) == ["YNG201", "YNG202", "YNG302", "YNG301"]


def test_reports_docstring_layout_rules() -> None:
    source = '''"""
Module description.
"""
import json


class Service:
    """
    Service description.
    """

    def execute(self) -> None:
        """
        Execute.
        """

        return None
'''
    assert _codes(source=source) == ["YNG104", "YNG105", "YNG106"]


def test_reports_definition_spacing_rules() -> None:
    source = '''def first() -> None:
    return None

def second() -> None:

    return None
'''
    assert _codes(source=source) == ["YNG401", "YNG403"]


def test_reports_class_method_spacing_rule() -> None:
    source = '''class Service:
    def first(self) -> None:
        return None
    def second(self) -> None:
        return None
'''
    assert _codes(source=source) == ["YNG402"]


def test_reports_short_wrapper_spacing_rule() -> None:
    source = '''def execute() -> object:
    prepare()

    return handler.execute()
'''
    assert _codes(source=source) == ["YNG501"]


def test_reports_direct_return_spacing_rule() -> None:
    source = '''def execute() -> object:
    result = handler.execute()

    return result
'''
    assert _codes(source=source) == ["YNG502"]


def test_allows_return_spacing_after_validation() -> None:
    source = '''def execute(article: object | None) -> object:
    if article is None:
        raise ValueError("missing")

    return article
'''
    assert _codes(source=source) == []


def test_result_detection_uses_marker_fields() -> None:
    payload = '''def execute() -> dict[str, object]:
    return { "message": "ok", "data": None }
'''
    result = '''def execute() -> dict[str, object]:
    return { "error": False, "message": "ok" }
'''

    assert _codes(source=payload) == []
    assert _codes(source=result) == ["YNG601"]


def test_reports_result_aliases() -> None:
    source = '''def execute() -> dict[str, object]:
    return { "success": True, "msg": "ok", "payload": None }
'''
    assert _codes(source=source) == ["YNG602"]


def test_tracks_local_result_dictionary() -> None:
    source = '''def execute() -> dict[str, object]:
    result = { "error": False, "code": "SUCCESS", "message": "ok" }
    return result
'''
    assert _codes(source=source) == ["YNG601"]


def test_reports_result_branch_field_mismatch() -> None:
    config = ResultConfig(required_fields=("error", "code"))
    source = '''def execute(ignored: bool) -> dict[str, object]:
    if ignored:
        return { "error": False, "code": "IGNORED" }
    return { "error": False, "code": "SUCCESS", "message": "ok" }
'''
    assert _codes(source=source, result_config=config) == ["YNG603"]


def test_validates_configured_typed_dict_schema() -> None:
    source = '''from typing import TypedDict


class OperationResult(TypedDict):
    error: bool
    code: str
    message: str
'''
    config = ResultConfig(typed_dict_names=("OperationResult",))
    assert _codes(source=source, result_config=config) == ["YNG601"]


def test_return_annotation_forces_result_dictionary_validation() -> None:
    source = '''from typing import TypedDict


class OperationResult(TypedDict):
    error: bool
    code: str
    message: str
    data: object | None


def execute() -> OperationResult:
    return { "message": "ok", "data": None }
'''
    config = ResultConfig(typed_dict_names=("OperationResult",))
    assert _codes(source=source, result_config=config) == ["YNG601"]


def test_supports_custom_result_fields() -> None:
    source = '''def execute() -> dict[str, object]:
    return { "ok": True, "value": None }
'''
    config = ResultConfig(required_fields=("ok", "value"), marker_fields=("ok",), aliases=())
    assert _codes(source=source, result_config=config) == []


def test_reports_import_order_within_group() -> None:
    source = "import json\nfrom pathlib import Path\n"
    assert _codes(source=source) == ["YNG400"]


def test_reports_syntax_error() -> None:
    assert _codes(source="def broken(:\n") == ["YNG000"]
