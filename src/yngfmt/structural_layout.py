"""
Structure-aware layout normalization that never uses line width.
"""

from typing import Final
import ast
import io
import re
import tokenize


_INDENT: Final[str] = "    "
_SAFE_LOCAL_CHILD_TYPES: Final[tuple[type[ast.expr], ...]] = (ast.Call, ast.Dict, ast.DictComp, ast.List, ast.ListComp, ast.Set, ast.SetComp, ast.Tuple)
_SIMPLE_CALL_ARGUMENT_TYPES: Final[tuple[type[ast.expr], ...]] = (ast.Attribute, ast.Constant, ast.JoinedStr, ast.Name)
_NESTED_EXPRESSION_PARENTS: Final[tuple[type[ast.AST], ...]] = (ast.Call, ast.Dict, ast.List, ast.Set, ast.Tuple)
_COMPLEX_STATEMENT_TYPES: Final[tuple[type[ast.stmt], ...]] = (ast.AsyncFor, ast.AsyncWith, ast.For, ast.If, ast.Match, ast.Raise, ast.Try, ast.While, ast.With)
_CHAIN_BREAK_PATTERN: Final[re.Pattern[str]] = re.compile(r"[ \t]*\r?\n[ \t]*\.")


def _character_column(line: str, byte_column: int) -> int:
    """
    Convert an AST UTF-8 byte column into a Python string column.
    """
    prefix: bytes = line.encode("utf-8")[:byte_column]
    return len(prefix.decode("utf-8"))


def _line_offsets(source: str) -> tuple[list[str], list[int]]:
    """
    Return source lines and their cumulative character offsets.
    """
    lines: list[str] = source.splitlines(keepends=True)
    offsets: list[int] = [0]
    for line in lines:
        offsets.append(
            offsets[-1] + len(line),
        )
    return lines, offsets


def _node_bounds(source: str, node: ast.expr) -> tuple[int, int] | None:
    """
    Return exact character offsets for one expression node.
    """
    if node.end_lineno is None or node.end_col_offset is None:
        return None

    lines, offsets = _line_offsets(source=source)
    start_line_index: int = node.lineno - 1
    end_line_index: int = node.end_lineno - 1
    if start_line_index >= len(lines) or end_line_index >= len(lines):
        return None

    start_column: int = _character_column(line=lines[start_line_index], byte_column=node.col_offset)
    end_column: int = _character_column(line=lines[end_line_index], byte_column=node.end_col_offset)
    return offsets[start_line_index] + start_column, offsets[end_line_index] + end_column


def _leading_whitespace(line: str) -> str:
    """
    Return leading horizontal whitespace from one source line.
    """
    return line[: len(line) - len(line.lstrip(" \t"))]


def _contains_comment(segment: str) -> bool:
    """
    Return whether a source segment contains a comment token.
    """
    return any(
        token.type == tokenize.COMMENT
        for token in tokenize.generate_tokens(
            io.StringIO(segment).readline,
        )
    )


def _is_implicit_string_concatenation(source: str, node: ast.expr) -> bool:
    """
    Return whether one constant is formed from adjacent string literal tokens.
    """
    if not isinstance(node, ast.Constant) or not isinstance(node.value, (str, bytes)):
        return False

    segment: str | None = ast.get_source_segment(source, node)
    if segment is None:
        return False

    string_token_count: int = sum(
        token.type == tokenize.STRING
        for token in tokenize.generate_tokens(
            io.StringIO(segment).readline,
        )
    )
    return string_token_count > 1


def _is_safe_local_child(source: str, child: ast.expr) -> bool:
    """
    Return whether a multi-line child can safely keep its own local expansion.
    """
    if isinstance(child, _SAFE_LOCAL_CHILD_TYPES):
        return True
    return _is_implicit_string_concatenation(source=source, node=child)


def _strip_outer_trailing_comma(line: str) -> str:
    """
    Remove a separator comma belonging to a now-compact outer wrapper.
    """
    stripped: str = line.rstrip()
    if not stripped.endswith(","):
        return line

    trailing_whitespace: str = line[len(stripped) :]
    return f"{stripped[:-1]}{trailing_whitespace}"


def _collapse_segment(segment: str, opener: str, closer: str) -> str | None:
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
    child_indent: str = _leading_whitespace(line=middle_lines[0])
    expected_child_indent: str = f"{outer_indent}{_INDENT}"
    if child_indent != expected_child_indent:
        return None
    if any(line.strip() and not line.startswith(child_indent) for line in middle_lines):
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
    return newline.join(
        [
            merged_first_line,
            *dedented_lines[1:-1],
            merged_last_line,
        ],
    )


def _single_multiline_child(source: str, node: ast.expr) -> tuple[ast.expr, str, str] | None:
    """
    Return one locally expandable child and the redundant parent delimiters.
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

    if not _is_safe_local_child(source=source, child=child):
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

        child_layout: tuple[ast.expr, str, str] | None = _single_multiline_child(source=source, node=node)
        if child_layout is None:
            continue

        _, opener, closer = child_layout
        bounds: tuple[int, int] | None = _node_bounds(source=source, node=node)
        if bounds is None:
            continue

        start_offset, end_offset = bounds
        segment: str = source[start_offset:end_offset]
        collapsed: str | None = _collapse_segment(segment=segment, opener=opener, closer=closer)
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


def _simple_call_replacement(source: str, node: ast.Call) -> str | None:
    """
    Return canonical compact text for a deterministic zero- or one-argument call.
    """
    argument_count: int = len(node.args) + len(node.keywords)
    if argument_count > 1:
        return None
    if any(isinstance(argument, ast.Starred) for argument in node.args):
        return None
    if any(keyword.arg is None for keyword in node.keywords):
        return None

    segment: str | None = ast.get_source_segment(source, node)
    function_text: str | None = ast.get_source_segment(source, node.func)
    if segment is None or function_text is None or _contains_comment(segment=segment):
        return None
    if "\n" not in segment and "\r" not in segment:
        return None

    function_text = _CHAIN_BREAK_PATTERN.sub(".", function_text)
    if "\n" in function_text or "\r" in function_text:
        return None

    if argument_count == 0:
        return f"{function_text}()"

    if node.args:
        argument: ast.expr = node.args[0]
        if not isinstance(argument, _SIMPLE_CALL_ARGUMENT_TYPES):
            return None
        argument_text: str | None = ast.get_source_segment(source, argument)
        if argument_text is None or "\n" in argument_text or "\r" in argument_text:
            return None
        return f"{function_text}({argument_text})"

    keyword: ast.keyword = node.keywords[0]
    if not isinstance(keyword.value, _SIMPLE_CALL_ARGUMENT_TYPES):
        return None
    value_text: str | None = ast.get_source_segment(source, keyword.value)
    if value_text is None or "\n" in value_text or "\r" in value_text:
        return None
    return f"{function_text}({keyword.arg}={value_text})"


def _compact_simple_call_once(source: str) -> str | None:
    """
    Compact the smallest deterministic top-level multiline call without consulting line width.
    """
    tree: ast.Module = ast.parse(source, type_comments=True)
    parents: dict[ast.AST, ast.AST] = {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }
    candidates: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(parents.get(node), _NESTED_EXPRESSION_PARENTS):
            continue
        replacement: str | None = _simple_call_replacement(source=source, node=node)
        if replacement is None:
            continue
        bounds: tuple[int, int] | None = _node_bounds(source=source, node=node)
        if bounds is None:
            continue
        candidates.append((bounds[0], bounds[1], replacement))

    if not candidates:
        return None

    start_offset, end_offset, replacement = min(
        candidates,
        key=lambda candidate: (candidate[1] - candidate[0], candidate[0]),
    )
    return f"{source[:start_offset]}{replacement}{source[end_offset:]}"


def compact_simple_calls(source: str) -> str:
    """
    Keep simple zero- and one-argument top-level calls on one line, including call chains.
    """
    current_source: str = source
    while True:
        compacted_source: str | None = _compact_simple_call_once(source=current_source)
        if compacted_source is None:
            return current_source
        current_source = compacted_source


def _body_without_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.stmt]:
    body: list[ast.stmt] = node.body
    if not body:
        return body
    first: ast.stmt = body[0]
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return body[1:]
    return body


def compact_thin_function_spacing(source: str) -> str:
    """
    Remove decorative blank lines from short straight-line function bodies.
    """
    tree: ast.Module = ast.parse(source, type_comments=True)
    lines: list[str] = source.splitlines(keepends=True)
    removals: list[tuple[int, int]] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        body: list[ast.stmt] = _body_without_docstring(node=node)
        if not 2 <= len(body) <= 3:
            continue
        if any(isinstance(statement, _COMPLEX_STATEMENT_TYPES) for statement in body):
            continue

        for previous, current in zip(body, body[1:]):
            previous_end: int = previous.end_lineno or previous.lineno
            current_start: int = current.lineno
            if current_start - previous_end <= 1:
                continue

            gap: list[str] = lines[previous_end : current_start - 1]
            if not gap or any(line.strip() for line in gap):
                continue
            removals.append((previous_end, current_start - 1))

    for start, end in reversed(removals):
        del lines[start:end]
    return "".join(lines)


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
