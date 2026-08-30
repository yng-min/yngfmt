"""
Compact multiline calls using expression structure and local call-run consistency.
"""

from typing import Final
import ast
import io
import re
import tokenize


_SIMPLE_ARGUMENT_TYPES: Final[tuple[type[ast.expr], ...]] = (
    ast.Attribute,
    ast.BinOp,
    ast.BoolOp,
    ast.Compare,
    ast.Constant,
    ast.JoinedStr,
    ast.Name,
    ast.Subscript,
    ast.UnaryOp,
)
_NON_FLAT_EXPRESSION_TYPES: Final[tuple[type[ast.expr], ...]] = (
    ast.Call,
    ast.Dict,
    ast.DictComp,
    ast.GeneratorExp,
    ast.IfExp,
    ast.Lambda,
    ast.List,
    ast.ListComp,
    ast.Set,
    ast.SetComp,
    ast.Tuple,
)
_NESTED_EXPRESSION_PARENTS: Final[tuple[type[ast.AST], ...]] = (
    ast.Call,
    ast.Dict,
    ast.List,
    ast.Set,
    ast.Tuple,
)
_HOMOGENEOUS_COMPACT_LIMIT: Final[int] = 200
_CAMEL_METHOD_FAMILY_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-z]+")


def _contains_comment(segment: str) -> bool:
    return any(
        token.type == tokenize.COMMENT
        for token in tokenize.generate_tokens(io.StringIO(segment).readline)
    )


def _contains_multiline_string(segment: str) -> bool:
    return any(
        token.type == tokenize.STRING and ("\n" in token.string or "\r" in token.string)
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


def _is_flat_simple_expression(node: ast.expr) -> bool:
    if not isinstance(node, _SIMPLE_ARGUMENT_TYPES):
        return False
    return not any(
        descendant is not node and isinstance(descendant, _NON_FLAT_EXPRESSION_TYPES)
        for descendant in ast.walk(node)
    )


def _single_line_expression(source: str, node: ast.expr) -> str | None:
    if not _is_flat_simple_expression(node=node):
        return None
    if node.end_lineno is None or node.lineno != node.end_lineno:
        return None

    segment: str | None = ast.get_source_segment(source, node)
    if segment is None or "\n" in segment or "\r" in segment:
        return None
    return segment


def _simple_replacement(source: str, node: ast.Call) -> str | None:
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


def _compact_expression(source: str, node: ast.expr) -> str | None:
    if node.end_lineno is not None and node.lineno == node.end_lineno:
        segment: str | None = ast.get_source_segment(source, node)
        if segment is not None and "\n" not in segment and "\r" not in segment:
            return segment

    if isinstance(node, ast.Call):
        function_text: str | None = ast.get_source_segment(source, node.func)
        if function_text is None or "\n" in function_text or "\r" in function_text:
            return None
        if any(isinstance(argument, ast.Starred) for argument in node.args):
            return None
        if any(keyword.arg is None for keyword in node.keywords):
            return None

        arguments: list[str] = []
        for argument in node.args:
            argument_text: str | None = _compact_expression(source=source, node=argument)
            if argument_text is None:
                return None
            arguments.append(argument_text)
        for keyword in node.keywords:
            value_text: str | None = _compact_expression(source=source, node=keyword.value)
            if value_text is None:
                return None
            arguments.append(f"{keyword.arg}={value_text}")
        return f"{function_text}({', '.join(arguments)})"

    if isinstance(node, ast.Dict):
        elements: list[str] = []
        for key, value in zip(node.keys, node.values):
            value_text: str | None = _compact_expression(source=source, node=value)
            if value_text is None:
                return None
            if key is None:
                elements.append(f"**{value_text}")
                continue
            key_text: str | None = _compact_expression(source=source, node=key)
            if key_text is None:
                return None
            elements.append(f"{key_text}: {value_text}")
        return "{}" if not elements else f"{{ {', '.join(elements)} }}"

    if isinstance(node, (ast.List, ast.Set, ast.Tuple)):
        items: list[str] = []
        for element in node.elts:
            element_text: str | None = _compact_expression(source=source, node=element)
            if element_text is None:
                return None
            items.append(element_text)

        if isinstance(node, ast.List):
            return f"[{', '.join(items)}]"
        if isinstance(node, ast.Set):
            return "set()" if not items else f"{{{', '.join(items)}}}"
        if len(items) == 1:
            return f"({items[0]},)"
        return f"({', '.join(items)})"

    return None


def _parent_map(tree: ast.Module) -> dict[ast.AST, ast.AST]:
    return {
        child: parent
        for parent in ast.walk(tree)
        for child in ast.iter_child_nodes(parent)
    }


def _method_family(method_name: str) -> str:
    if method_name.startswith("_"):
        return method_name
    if "_" in method_name:
        return method_name.split("_", 1)[0]

    match: re.Match[str] | None = _CAMEL_METHOD_FAMILY_PATTERN.match(method_name)
    if match is not None and match.end() < len(method_name):
        return match.group(0)
    return method_name


def _call_family(node: ast.Call) -> tuple[str, str] | None:
    if not isinstance(node.func, ast.Attribute):
        return None
    receiver: str = ast.dump(node.func.value, annotate_fields=True, include_attributes=False)
    return receiver, _method_family(method_name=node.func.attr)


def _call_statement(statement: ast.stmt) -> ast.Call | None:
    if not isinstance(statement, ast.Expr):
        return None
    value: ast.expr = statement.value.value if isinstance(statement.value, ast.Await) else statement.value
    return value if isinstance(value, ast.Call) else None


def _statement_blocks(tree: ast.Module) -> list[list[ast.stmt]]:
    blocks: list[list[ast.stmt]] = []
    for node in ast.walk(tree):
        for _, value in ast.iter_fields(node):
            if not isinstance(value, list) or not value:
                continue
            if all(isinstance(item, ast.stmt) for item in value):
                blocks.append(value)
    return blocks


def _homogeneous_runs(tree: ast.Module) -> list[list[ast.Call]]:
    runs: list[list[ast.Call]] = []
    for block in _statement_blocks(tree=tree):
        current_key: tuple[str, str] | None = None
        current_run: list[ast.Call] = []

        def flush() -> None:
            nonlocal current_key, current_run
            if len(current_run) >= 2:
                runs.append(current_run)
            current_key = None
            current_run = []

        for statement in block:
            call: ast.Call | None = _call_statement(statement=statement)
            if call is None:
                flush()
                continue

            key: tuple[str, str] | None = _call_family(node=call)
            if key is None:
                flush()
                continue
            if key != current_key:
                flush()
                current_key = key
            current_run.append(call)
        flush()
    return runs


def _homogeneous_replacement(source: str, node: ast.Call) -> str | None:
    if node.end_lineno is None or node.lineno == node.end_lineno:
        return None

    segment: str | None = ast.get_source_segment(source, node)
    if segment is None or _contains_comment(segment=segment) or _contains_multiline_string(segment=segment):
        return None

    replacement: str | None = _compact_expression(source=source, node=node)
    if replacement is None:
        return None

    line_prefix: str = source.splitlines()[node.lineno - 1][:node.col_offset]
    if len(line_prefix) + len(replacement) > _HOMOGENEOUS_COMPACT_LIMIT:
        return None
    return replacement


def _compact_simple_once(source: str) -> str | None:
    tree: ast.Module = ast.parse(source, type_comments=True)
    parents: dict[ast.AST, ast.AST] = _parent_map(tree=tree)
    candidates: list[tuple[int, int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(parents.get(node), _NESTED_EXPRESSION_PARENTS):
            continue

        replacement: str | None = _simple_replacement(source=source, node=node)
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


def _compact_homogeneous_once(source: str) -> str | None:
    tree: ast.Module = ast.parse(source, type_comments=True)
    candidates: list[tuple[int, int, str]] = []
    for run in _homogeneous_runs(tree=tree):
        for node in run:
            replacement: str | None = _homogeneous_replacement(source=source, node=node)
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
    Compact structurally simple calls, then normalize homogeneous call runs.
    """
    current_source: str = source
    while True:
        compacted_source: str | None = _compact_simple_once(source=current_source)
        if compacted_source is None:
            break
        current_source = compacted_source

    while True:
        compacted_source = _compact_homogeneous_once(source=current_source)
        if compacted_source is None:
            return current_source
        current_source = compacted_source
