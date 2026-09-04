"""
Formatter engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final
import ast
import inspect

import autopep8

from yngfmt.imports import ImportConfig, sort_imports

from yngfmt.transforms import apply_custom_transforms


_MECHANICAL_FIXES: Final[tuple[str, ...]] = (
    "E101",
    "E111",
    "E112",
    "E113",
    "E114",
    "E115",
    "E116",
    "E117",
    "E121",
    "E122",
    "E123",
    "E124",
    "E125",
    "E126",
    "E127",
    "E128",
    "E129",
    "E131",
    "E133",
    "E201",
    "E202",
    "E204",
    "E211",
    "E221",
    "E222",
    "E223",
    "E224",
    "E225",
    "E227",
    "E228",
    "E231",
    "E251",
    "E252",
    "E271",
    "E272",
    "E273",
    "E274",
    "E275",
    "W291",
    "W292",
    "W293",
    "W391",
)


@dataclass(frozen=True, slots=True)
class FormatResult:
    """
    Represent the result of formatting one file.
    """
    path: Path
    changed: bool
    source: str


def _normalize_docstring_values(tree: ast.Module) -> None:
    """
    Normalize docstring constants so delimiter-only layout changes remain equivalent.
    """
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue

        statement = body[0]
        if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Constant):
            continue
        if not isinstance(statement.value.value, str):
            continue
        statement.value.value = inspect.cleandoc(statement.value.value)


def _ast_signature(source: str) -> str:
    """
    Return a location-independent syntax-tree signature for semantic safety checks.
    """
    tree: ast.Module = ast.parse(source, type_comments=True)
    _normalize_docstring_values(tree=tree)
    for type_ignore in tree.type_ignores:
        type_ignore.lineno = 0
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def _require_ast_equivalence(before: str, after: str, stage: str) -> None:
    """
    Reject a source rewrite when it changes the parsed Python syntax tree.
    """
    if _ast_signature(source=before) == _ast_signature(source=after):
        return
    raise ValueError(f"yngfmt {stage} changed the Python syntax tree")


def _format_mechanical_whitespace(source: str) -> str:
    """
    Normalize explicitly selected mechanical whitespace without width-based rewriting.
    """
    return autopep8.fix_code(
        source,
        options={
            "select": list(_MECHANICAL_FIXES),
        },
        apply_config=False,
    )


def format_code(
    source: str,
    *,
    import_config: ImportConfig = ImportConfig(),
) -> str:
    """
    Format Python source according to the supported guide rules.
    """
    whitespace_formatted: str = _format_mechanical_whitespace(source=source)
    _require_ast_equivalence(before=source, after=whitespace_formatted, stage="mechanical whitespace pass")

    import_formatted: str = sort_imports(source=whitespace_formatted, config=import_config)
    custom_formatted: str = apply_custom_transforms(source=import_formatted)
    _require_ast_equivalence(before=import_formatted, after=custom_formatted, stage="custom transform pass")
    return custom_formatted


def format_path(
    path: Path,
    *,
    check: bool = False,
    import_config: ImportConfig = ImportConfig(),
) -> FormatResult:
    """
    Format one Python file and optionally write the result.
    """
    source: str = path.read_text(encoding="utf-8")
    formatted_source: str = format_code(source=source, import_config=import_config)
    changed: bool = source != formatted_source

    if changed and not check:
        path.write_text(formatted_source, encoding="utf-8")

    return FormatResult(path=path, changed=changed, source=formatted_source)
