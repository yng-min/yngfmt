"""
Compact multiline calls whose arguments are all structurally simple.
"""

from typing import Final
import ast
import io
import tokenize


_SIMPLE_ARGUMENT_TYPES: Final[tuple[type[ast.expr], ...]] = (
    ast.Attribute,
    ast.BinOp,
    ast.Compare,
    ast.Constant,
    ast.JoinedStr,
    ast.Name,
    ast.UnaryOp,
)
_NESTED_EXPRESSION_PARENTS: Final[tuple[type[ast.AST], ...]] = (
    ast.Call,
    ast.Dict,
    ast.List,
    ast.Set,
    ast.Tuple,
)


def _contains_comment(segment: str) -> bool:
    return any(
        token.type == tokenize.COMMENT
        for token in tokenize.generate_tokens(io.StringIO(segment).readline)
    )


def _node_bounds(source: str, node: ast.expr) -> tuple[int, int] | None:
    if node.end_lineno is None or node.end_col_offset is None:
        return None

    lines: list[str] = source.splitlines(keepends=True)
    offsets: list[int] = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    start_line_index: int = node.lineno - 1
    end_line_index: int = node.end_lineno - 1
    if start_line_index >= len(lines) or end_line_index >= len(lines):
        return None

    start_prefix: bytes = lines[start_line_index].encode("utf-8")[:node.col_offset]
    end_prefix: bytes = lines[end_line_index].encode("utf-8")[:node.end_col_offset]
    start_column: int = len(start_prefix.decode("utf-8"))
    end_column: int = len(end_prefix.decode("utf-8"))
    return offsets[start_line_index] + start_column, offsets[end_line_index] + end_column


def _single_line_expression(source: str, node: ast.expr) -> str | None:
    if not isinstance(node, _SIMPLE_ARGUMENT_TYPES):
        return None
    if node.end_lineno is None or node.lineno != node.end_lineno:
        return None

    segment: str | None = ast.get_source_segment(source, node)
    if segment is None or "\n" in segment or "\r" in segment:
        return None
    return segment


def _replacement(source: str, node: ast.Call) -> str | None:
    argument_count: int = len(node.args) + len(node.keywords)
    if argument_count < 2:
        return None
    if node.end_lineno is None or node.lineno == node.end_lineno:
        return None
    if any(isinstance(argument, ast.Starred) for argument in node.args):
        return None
    if any(keyword.arg is None for keyword in node.keywords):
        return None

    call_segment: str | None = ast.get_source_segment(source, node)
    function_text: str | None = ast.get_source_segment(source, node.func)
    if call_segment is None or function_text is None:
        return None
    if _contains_comment(segment=call_segment):
        return None
    if "\n" in function_text or "\r" in function_text:
        return None

    arguments: list[str] = []
    for argument in node.args:
        argument_text: str | None = _single_line_expression(source=source, node=argument)
        if argument_text is None:
            return None
        arguments.append(argument_text)

    for keyword in node.keywords:
        value_text: str | None = _single_line_expression(source=source, node=keyword.value)
        if value_text is None:
            return None
        arguments.append(f"{keyword.arg}={value_text}")

    return f"{function_text}({', '.join(arguments)})"


def _parent_map(tree: ast.Module) -> dict[ast.AST, ast.AST]:
    return {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }


def _compact_once(source: str) -> str | None:
    tree: ast.Module = ast.parse(source, type_comments=True)
    parents: dict[ast.AST, ast.AST] = _parent_map(tree=tree)
    candidates: list[tuple[int, int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(parents.get(node), _NESTED_EXPRESSION_PARENTS):
            continue

        replacement: str | None = _replacement(source=source, node=node)
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


def compact_multi_simple_calls(source: str) -> str:
    """
    Keep top-level multiline calls compact when every argument is structurally simple.
    """
    current_source: str = source
    while True:
        compacted_source: str | None = _compact_once(source=current_source)
        if compacted_source is None:
            return current_source
        current_source = compacted_source
