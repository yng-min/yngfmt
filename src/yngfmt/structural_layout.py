"""
Structure-aware layout normalization that never uses line width.
"""

from typing import Final
import ast
import io
import tokenize


_INDENT: Final[str] = "    "
_IGNORED_TOKEN_TYPES: Final[frozenset[int]] = frozenset({
    tokenize.DEDENT,
    tokenize.ENDMARKER,
    tokenize.INDENT,
    tokenize.NEWLINE,
    tokenize.NL,
})


def _character_column(line: str, byte_column: int) -> int:
    """
    Convert an AST UTF-8 byte column into a Python string column.
    """
    prefix: bytes = line.encode("utf-8")[:byte_column]
    return len(prefix.decode("utf-8"))


def _node_bounds(source: str, node: ast.expr) -> tuple[int, int] | None:
    """
    Return exact character offsets for one expression node.
    """
    if node.end_lineno is None or node.end_col_offset is None:
        return None

    lines: list[str] = source.splitlines(keepends=True)
    start_line_index: int = node.lineno - 1
    end_line_index: int = node.end_lineno - 1
    if start_line_index >= len(lines) or end_line_index >= len(lines):
        return None

    start_column: int = _character_column(
        line=lines[start_line_index],
        byte_column=node.col_offset,
    )
    end_column: int = _character_column(
        line=lines[end_line_index],
        byte_column=node.end_col_offset,
    )
    start_offset: int = sum(len(line) for line in lines[:start_line_index]) + start_column
    end_offset: int = sum(len(line) for line in lines[:end_line_index]) + end_column
    return start_offset, end_offset


def _leading_whitespace(line: str) -> str:
    """
    Return leading horizontal whitespace from one source line.
    """
    return line[: len(line) - len(line.lstrip(" \t"))]


def _contains_comment(segment: str) -> bool:
    """
    Return whether a source segment contains a comment token.
    """
    return any(token.type == tokenize.COMMENT
    for token in tokenize.generate_tokens(io.StringIO(segment).readline))


def _strip_outer_trailing_comma(line: str) -> str:
    """
    Remove a separator comma belonging to a now-compact outer wrapper.
    """
    stripped: str = line.rstrip()
    if not stripped.endswith(","):
        return line

    trailing_whitespace: str = line[len(stripped) :]
    return f"{stripped[:-1]}{trailing_whitespace}"


def _collapse_segment(
    segment: str,
    opener: str,
    closer: str,
) -> str | None:
    """
    Collapse one redundant parent wrapper while leaving its child multi-line.
    """
    if _contains_comment(segment=segment):
        return None

    newline: str = "\r\n" if "\r\n" in segment else "\n"
    lines: list[str] = segment.splitlines()
    if len(lines) < 3:
        return None

    first_line: str = lines[0]
    last_line: str = lines[-1]
    if not first_line.rstrip().endswith(opener) or last_line.strip() != closer:
        return None

    middle_lines: list[str] = lines[1:-1]
    if not middle_lines or any(not line.strip() for line in middle_lines):
        return None

    outer_indent: str = _leading_whitespace(line=last_line)
    body_indent: str = _leading_whitespace(line=middle_lines[0])
    if body_indent != f"{outer_indent}{_INDENT}":
        return None
    if any(line.strip() and not line.startswith(body_indent)
    for line in middle_lines):
        return None

    dedented_lines: list[str] = [
        line[len(_INDENT) :] if line.strip() else line
        for line in middle_lines
    ]
    dedented_lines[-1] = _strip_outer_trailing_comma(line=dedented_lines[-1])

    first_body_line: str = dedented_lines[0]
    last_body_line: str = dedented_lines[-1]
    if not first_body_line.startswith(outer_indent) or not last_body_line.startswith(outer_indent):
        return None

    merged_first_line: str = f"{first_line}{first_body_line[len(outer_indent):]}"
    merged_last_line: str = f"{last_body_line}{last_line[len(outer_indent):]}"
    return newline.join([merged_first_line, *dedented_lines[1:-1], merged_last_line])


def _single_multiline_child(node: ast.expr) -> tuple[ast.expr, str, str] | None:
    """
    Return a single multi-line child and its parent delimiters when collapsible.
    """
    child: ast.expr
    opener: str
    closer: str

    if isinstance(node, ast.Call):
        if len(node.args) + len(node.keywords) != 1:
            return None
        child = node.args[0] if node.args else node.keywords[0].value
        opener = "("
        closer = ")"
    elif isinstance(node, ast.List):
        if len(node.elts) != 1:
            return None
        child = node.elts[0]
        opener = "["
        closer = "]"
    else:
        return None

    if child.end_lineno is None or child.lineno == child.end_lineno:
        return None
    return child, opener, closer


def _collapse_once(source: str) -> str | None:
    """
    Collapse the smallest currently redundant outer expansion.
    """
    tree: ast.Module = ast.parse(source, type_comments=True)
    candidates: list[tuple[int, int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.expr):
            continue

        child_layout: tuple[ast.expr, str, str] | None = _single_multiline_child(node=node)
        if child_layout is None:
            continue

        _, opener, closer = child_layout
        bounds: tuple[int, int] | None = _node_bounds(source=source, node=node)
        if bounds is None:
            continue

        start_offset, end_offset = bounds
        segment: str = source[start_offset:end_offset]
        collapsed: str | None = _collapse_segment(
            segment=segment,
            opener=opener,
            closer=closer,
        )
        if collapsed is None or collapsed == segment:
            continue
        candidates.append((start_offset, end_offset, collapsed))

    if not candidates:
        return None

    start_offset, end_offset, collapsed = min(
        candidates,
        key=lambda candidate: (candidate[1] - candidate[0], candidate[0]),
    )
    return f"{source[:start_offset]}{collapsed}{source[end_offset:]}"


def collapse_redundant_outer_expansions(source: str) -> str:
    """
    Keep only the smallest expression structure that actually needs multiple lines.
    """
    current_source: str = source
    while True:
        collapsed_source: str | None = _collapse_once(source=current_source)
        if collapsed_source is None:
            return current_source
        current_source = collapsed_source
