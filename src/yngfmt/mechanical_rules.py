"""
Deterministic style-guide checks that should not rewrite source semantics.
"""

from dataclasses import dataclass
from typing import Final
import ast
import io
import re
import tokenize

from yngfmt.layout_policy import LayoutKind, LayoutStyle, layout_contexts


_DOCSTRING_CLOSING_LINE_PATTERN: Final[re.Pattern[str]] = re.compile(r"(?:\r\n|\n)[ \t]*\Z")


@dataclass(frozen=True, slots=True)
class MechanicalIssue:
    """
    Describe one deterministic style-guide violation without repository context.
    """
    line: int
    column: int
    code: str
    message: str


def _docstring_value(body: list[ast.stmt]) -> ast.Constant | None:
    if not body:
        return None

    statement: ast.stmt = body[0]
    if not isinstance(statement, ast.Expr):
        return None
    if not isinstance(statement.value, ast.Constant):
        return None
    if not isinstance(statement.value.value, str):
        return None
    return statement.value


def _docstring_positions(tree: ast.Module) -> set[tuple[int, int]]:
    positions: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        docstring_value: ast.Constant | None = _docstring_value(body=node.body)
        if docstring_value is not None:
            positions.add((docstring_value.lineno, docstring_value.col_offset))
    return positions


def _string_prefix_and_quote(token_value: str) -> tuple[str, str] | None:
    match: re.Match[str] | None = re.match(r"(?i)^([rubf]*)(\"\"\"|'{3}|\"|')", token_value)
    if match is None:
        return None
    return match.group(1), match.group(2)


def _check_docstring_delimiter_layout(source: str, tree: ast.Module) -> list[MechanicalIssue]:
    positions: set[tuple[int, int]] = _docstring_positions(tree=tree)
    diagnostics: list[MechanicalIssue] = []

    for token in tokenize.generate_tokens(
        io.StringIO(source).readline,
    ):
        if token.type != tokenize.STRING or token.start not in positions:
            continue

        parsed: tuple[str, str] | None = _string_prefix_and_quote(token_value=token.string)
        if parsed is None:
            continue
        prefix, quote = parsed
        if quote != "\"\"\"":
            continue

        body: str = token.string[len(prefix) + len(quote) : -len(quote)]
        if not body.startswith(("\n", "\r\n")):
            diagnostics.append(MechanicalIssue(line=token.start[0], column=token.start[1] + 1, code="YNG107", message="docstring content must start on the line after opening quotes"))
        if _DOCSTRING_CLOSING_LINE_PATTERN.search(body) is None:
            diagnostics.append(MechanicalIssue(line=token.end[0], column=max(1, token.end[1] - 2), code="YNG108", message="docstring closing quotes must be on their own line"))
    return diagnostics


def _check_dictionary_spacing(source: str, tree: ast.Module) -> list[MechanicalIssue]:
    diagnostics: list[MechanicalIssue] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict) or node.lineno != node.end_lineno:
            continue

        segment: str | None = ast.get_source_segment(source, node)
        if segment is None:
            continue

        if not node.keys:
            is_valid: bool = segment == "{}"
        else:
            is_valid = segment.startswith("{ ") and segment.endswith(" }")
        if is_valid:
            continue

        diagnostics.append(MechanicalIssue(line=node.lineno, column=node.col_offset + 1, code="YNG109", message="single-line dictionary literal has non-canonical inner spacing"))
    return diagnostics


def _check_container_layout(source: str, tree: ast.Module) -> list[MechanicalIssue]:
    del tree
    diagnostics: list[MechanicalIssue] = []
    for context in layout_contexts(source=source):
        if context.expected_style == LayoutStyle.PRESERVE:
            continue

        if context.actual_style != context.expected_style:
            if context.kind == LayoutKind.CALL and context.expected_style == LayoutStyle.COMPACT:
                code: str = "YNG704" if not context.items else "YNG701"
                message: str = (
                    "zero-argument call must stay on one line"
                    if not context.items
                    else "structurally simple call must use compact layout"
                )
            else:
                code = "YNG705"
                message = f"{context.kind.value} must use {context.expected_style.value} canonical layout"
            diagnostics.append(MechanicalIssue(line=context.line, column=context.column, code=code, message=message))
            continue

        if context.actual_style == LayoutStyle.EXPANDED and not context.has_trailing_comma:
            code = "YNG702" if context.kind == LayoutKind.CALL else "YNG706"
            diagnostics.append(MechanicalIssue(line=context.line, column=context.column, code=code, message=f"expanded {context.kind.value} must end its final item with a trailing comma"))
        elif (
            context.actual_style == LayoutStyle.COMPACT
            and context.has_trailing_comma
            and not (
                context.kind == LayoutKind.TUPLE
                and len(context.items) == 1
            )
        ):
            code = "YNG703" if context.kind == LayoutKind.CALL else "YNG706"
            diagnostics.append(MechanicalIssue(line=context.line, column=context.column, code=code, message=f"compact {context.kind.value} must not use a trailing comma"))
    return diagnostics


def check_mechanical_rules(source: str, tree: ast.Module) -> list[MechanicalIssue]:
    """
    Return deterministic style-guide violations not owned by the import sorter.
    """
    diagnostics: list[MechanicalIssue] = [
        *_check_docstring_delimiter_layout(source=source, tree=tree),
        *_check_dictionary_spacing(source=source, tree=tree),
        *_check_container_layout(source=source, tree=tree),
    ]
    return diagnostics
