"""
Regression tests for formatter and linter integration behavior.
"""

from pathlib import Path

from yngfmt.formatter import format_code

from yngfmt.linter import ResultConfig, lint_code, load_result_config


def _codes(source: str, result_config: ResultConfig = ResultConfig()) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in lint_code(
            source=source,
            path=Path("test.py"),
            result_config=result_config,
        )
    ]


def test_formats_docstring_delimiters_and_definition_spacing() -> None:
    source: str = '''class Service:
    """Service description."""

    def execute(self) -> None:
        """Execute."""
        return None
'''
    assert format_code(source) == '''class Service:
    """
    Service description.
    """
    def execute(self) -> None:
        """
        Execute.
        """
        return None
'''


def test_typing_literal_uses_double_quotes_while_mapping_key_uses_single_quotes() -> None:
    source: str = '''from typing import Literal

Format = Literal['native', 'vst3']
value = data["name"]
'''
    assert format_code(source) == '''from typing import Literal


Format = Literal["native", "vst3"]
value = data['name']
'''


def test_linter_accepts_private_pascal_case_class() -> None:
    source: str = '''class _InternalCache:
    pass
'''
    assert "YNG201" not in _codes(source=source)


def test_linter_accepts_chained_zero_argument_call_on_multiline_expression() -> None:
    source: str = '''value = (
    root
    / "Assets"
    / "Audio"
).as_posix()
'''
    assert "YNG704" not in _codes(source=source)


def test_linter_rejects_actually_expanded_zero_argument_call() -> None:
    source: str = '''value = process(
)
'''
    assert "YNG704" in _codes(source=source)


def test_result_rules_are_disabled_without_project_opt_in(tmp_path: Path) -> None:
    pyproject_path: Path = tmp_path / "pyproject.toml"
    pyproject_path.write_text("[project]\nname = \"example\"\n", encoding="utf-8")
    config: ResultConfig = load_result_config(pyproject_path)
    assert config.enabled is False

    source: str = '''def execute() -> dict[str, object]:
    return { "error": True, "code": "FAILED", "message": "failed" }
'''
    assert "YNG601" not in _codes(source=source, result_config=config)
