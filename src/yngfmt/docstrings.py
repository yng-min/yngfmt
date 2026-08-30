"""
Docstring layout normalization for mechanically safe delimiter and spacing rules.
"""

from typing import Final
import ast
import io
import re
import tokenize


_STRING_PREFIX_AND_QUOTE: Final[re.Pattern[str]] = re.compile(r"(?i)^([rubf]*)(\"\"\"|'{3}|\"|')")


def _is_docstring_statement(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _docstring_positions(tree: ast.Module) -> set[tuple[int, int]]:
    positions: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and _is_docstring_statement(body[0]):
            positions.add((body[0].value.lineno, body[0].value.col_offset))
    return positions


def normalize_docstring_delimiters(source: str) -> str:
    """
    Put triple-double docstring content and closing delimiters on dedicated lines.
    """
    tree: ast.Module = ast.parse(source, type_comments=True)
    positions: set[tuple[int, int]] = _docstring_positions(tree=tree)
    lines: list[str] = source.splitlines(keepends=True)
    line_offsets: list[int] = [0]
    for line in lines:
        line_offsets.append(line_offsets[-1] + len(line))

    replacements: list[tuple[int, int, str]] = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.STRING or token.start not in positions:
            continue

        match: re.Match[str] | None = _STRING_PREFIX_AND_QUOTE.match(token.string)
        if match is None or match.group(2) != "\"\"\"":
            continue

        prefix: str = match.group(1)
        quote: str = match.group(2)
        body: str = token.string[len(prefix) + len(quote) : -len(quote)]
        newline: str = "\r\n" if "\r\n" in token.string else "\n"
        indent: str = " " * token.start[1]

        if not body.startswith(("\n", "\r\n")):
            body = f"{newline}{indent}{body}"
        if not body.endswith((f"\n{indent}", f"\r\n{indent}")):
            body = f"{body}{newline}{indent}"

        replacement: str = f"{prefix}{quote}{body}{quote}"
        if replacement == token.string:
            continue

        start: int = line_offsets[token.start[0] - 1] + token.start[1]
        end: int = line_offsets[token.end[0] - 1] + token.end[1]
        replacements.append((start, end, replacement))

    formatted: str = source
    for start, end, replacement in reversed(replacements):
        formatted = f"{formatted[:start]}{replacement}{formatted[end:]}"
    return formatted


def compact_definition_docstring_spacing(source: str) -> str:
    """
    Remove pure blank lines after class or function docstrings without moving comments.
    """
    tree: ast.Module = ast.parse(source, type_comments=True)
    lines: list[str] = source.splitlines(keepends=True)
    removals: list[tuple[int, int]] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if len(node.body) < 2 or not _is_docstring_statement(node.body[0]):
            continue

        docstring: ast.stmt = node.body[0]
        next_statement: ast.stmt = node.body[1]
        docstring_end: int = docstring.end_lineno or docstring.lineno
        if next_statement.lineno - docstring_end <= 1:
            continue

        gap: list[str] = lines[docstring_end : next_statement.lineno - 1]
        if not gap or any(line.strip() for line in gap):
            continue
        removals.append((docstring_end, next_statement.lineno - 1))

    for start, end in reversed(removals):
        del lines[start:end]
    return "".join(lines)
