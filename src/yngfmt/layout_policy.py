"""
Shared structural and density-based layout policy.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Final
import ast
import io
import tokenize


COMPACT_SOFT_LIMIT: Final[int] = 200
NAMED_ITEM_LIMIT: Final[int] = 5
LONG_NAME_LIMIT: Final[int] = 24
LONG_NAMED_ITEM_LIMIT: Final[int] = 64
DENSE_ITEM_LENGTH: Final[int] = 32
LONG_VALUE_LENGTH: Final[int] = 36
MIN_DENSITY_ITEM_COUNT: Final[int] = 3
COHORT_MIN_SIZE: Final[int] = 3
_INDENT: Final[str] = "    "
_SUPPORTED_CONTAINER_TYPES: Final[tuple[type[ast.expr], ...]] = (ast.Call, ast.Dict, ast.List, ast.Set, ast.Tuple)
_HARD_COMPLEX_EXPRESSION_TYPES: Final[tuple[type[ast.expr], ...]] = (ast.DictComp, ast.GeneratorExp, ast.IfExp, ast.Lambda, ast.ListComp, ast.NamedExpr, ast.SetComp)
_IGNORED_TRAILING_TOKEN_TYPES: Final[frozenset[int]] = frozenset({tokenize.COMMENT, tokenize.DEDENT, tokenize.INDENT, tokenize.NEWLINE, tokenize.NL})


class LayoutKind(StrEnum):
    """
    Identify a supported delimited container.
    """
    CALL = "function call"
    FUNCTION_DEFINITION = "function definition"
    DICTIONARY = "dictionary"
    LIST = "list"
    TUPLE = "tuple"
    SET = "set"


class LayoutStyle(StrEnum):
    """
    Describe the canonical shape selected by the layout policy.
    """
    COMPACT = "compact"
    EXPANDED = "expanded"
    PRESERVE = "preserve"


@dataclass(frozen=True, slots=True)
class LayoutItem:
    """
    Describe one top-level item without container-specific syntax.
    """
    text: str
    rendered_length: int
    value_length: int
    name_length: int | None
    is_named: bool
    is_multiline: bool
    has_nested_structure: bool


@dataclass(frozen=True, slots=True)
class LayoutContext:
    """
    Hold the facts shared by formatter and linter layout decisions.
    """
    kind: LayoutKind
    items: tuple[LayoutItem, ...]
    compact_length: int
    actual_style: LayoutStyle
    expected_style: LayoutStyle
    has_trailing_comma: bool
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class _LayoutDecision:
    style: LayoutStyle
    hard_expansion: bool


@dataclass(frozen=True, slots=True)
class _SourceToken:
    token: tokenize.TokenInfo
    start_offset: int
    end_offset: int


@dataclass(frozen=True, slots=True)
class _LayoutTarget:
    context: LayoutContext
    start_offset: int
    end_offset: int
    opener: str
    closer: str
    base_indent: str
    node: ast.AST
    hard_expansion: bool


def _character_column(line: str, byte_column: int) -> int:
    prefix: bytes = line.encode("utf-8")[:byte_column]
    return len(prefix.decode("utf-8"))


def _line_offsets(source: str) -> tuple[list[str], list[int]]:
    lines: list[str] = source.splitlines(keepends=True)
    offsets: list[int] = [0]
    for line in lines:
        offsets.append(
            offsets[-1] + len(line),
        )
    return lines, offsets


def _position_offset(offsets: list[int], position: tuple[int, int]) -> int:
    line, column = position
    return offsets[line - 1] + column


def _source_tokens(source: str, offsets: list[int]) -> list[_SourceToken]:
    return [
        _SourceToken(
            token=token,
            start_offset=_position_offset(offsets=offsets, position=token.start),
            end_offset=_position_offset(offsets=offsets, position=token.end),
        )
        for token in tokenize.generate_tokens(
            io.StringIO(source).readline,
        )
    ]


def _node_bounds(source: str, lines: list[str], offsets: list[int], node: ast.AST) -> tuple[int, int] | None:
    del source
    end_lineno: int | None = getattr(node, "end_lineno", None)
    end_col_offset: int | None = getattr(node, "end_col_offset", None)
    lineno: int | None = getattr(node, "lineno", None)
    col_offset: int | None = getattr(node, "col_offset", None)
    if (
        lineno is None
        or col_offset is None
        or end_lineno is None
        or end_col_offset is None
    ):
        return None

    start_line_index: int = lineno - 1
    end_line_index: int = end_lineno - 1
    if start_line_index >= len(lines) or end_line_index >= len(lines):
        return None

    start_column: int = _character_column(line=lines[start_line_index], byte_column=col_offset)
    end_column: int = _character_column(line=lines[end_line_index], byte_column=end_col_offset)
    return (offsets[start_line_index] + start_column, offsets[end_line_index] + end_column)


def _normalized_node_text(source: str, lines: list[str], offsets: list[int], node: ast.AST) -> str | None:
    bounds: tuple[int, int] | None = _node_bounds(source=source, lines=lines, offsets=offsets, node=node)
    if bounds is None:
        return None

    segment: str = source[bounds[0]:bounds[1]]
    segment_lines: list[str] = segment.splitlines()
    if len(segment_lines) <= 1:
        return segment.strip()

    continuation_lines: list[str] = [
        line
        for line in segment_lines[1:]
        if line.strip()
    ]
    if not continuation_lines:
        return segment.strip()

    continuation_indent: int = min(
        len(line) - len(line.lstrip(" \t"))
        for line in continuation_lines
    )
    normalized_lines: list[str] = [segment_lines[0].strip()]
    normalized_lines.extend(
        line[continuation_indent:].rstrip()
        if line.strip()
        else ""
        for line in segment_lines[1:]
    )
    return "\n".join(normalized_lines).rstrip()


def _contains_comment(segment: str) -> bool:
    return any(
        token.type == tokenize.COMMENT
        for token in tokenize.generate_tokens(
            io.StringIO(segment).readline,
        )
    )


def _contains_multiline_string(segment: str) -> bool:
    return any(
        token.type == tokenize.STRING
        and ("\n" in token.string or "\r" in token.string)
        for token in tokenize.generate_tokens(
            io.StringIO(segment).readline,
        )
    )


def _layout_item(
    text: str,
    *,
    value_length: int | None = None,
    name_length: int | None = None,
    is_named: bool = False,
    has_nested_structure: bool = False,
) -> LayoutItem:
    rendered_text: str = text.replace("\n", "").replace("\r", "")
    return LayoutItem(
        text=text,
        rendered_length=len(rendered_text),
        value_length=len(rendered_text) if value_length is None else value_length,
        name_length=name_length,
        is_named=is_named,
        is_multiline="\n" in text or "\r" in text,
        has_nested_structure=has_nested_structure,
    )


def _unpacking_item_text(prefix: str, value_text: str, node: ast.expr) -> str:
    if isinstance(node, (ast.IfExp, ast.Lambda, ast.NamedExpr)):
        return f"{prefix}({value_text})"
    return f"{prefix}{value_text}"


def _strict_majority(count: int, total: int) -> bool:
    return total >= MIN_DENSITY_ITEM_COUNT and count * 2 > total


def _layout_decision(items: tuple[LayoutItem, ...], compact_length: int, *, preserve: bool = False) -> _LayoutDecision:
    if preserve:
        return _LayoutDecision(style=LayoutStyle.PRESERVE, hard_expansion=False)
    if not items:
        return _LayoutDecision(style=LayoutStyle.COMPACT, hard_expansion=False)
    if any(item.has_nested_structure for item in items):
        return _LayoutDecision(style=LayoutStyle.EXPANDED, hard_expansion=True)
    if compact_length > COMPACT_SOFT_LIMIT:
        return _LayoutDecision(style=LayoutStyle.EXPANDED, hard_expansion=True)

    named_items: tuple[LayoutItem, ...] = tuple(
        item
        for item in items
        if item.is_named
    )
    if len(named_items) >= NAMED_ITEM_LIMIT:
        return _LayoutDecision(style=LayoutStyle.EXPANDED, hard_expansion=False)

    long_name_count: int = sum(
        (item.name_length or 0) >= LONG_NAME_LIMIT
        for item in named_items
    )
    if _strict_majority(count=long_name_count, total=len(named_items)):
        return _LayoutDecision(style=LayoutStyle.EXPANDED, hard_expansion=False)

    long_named_item_count: int = sum(
        item.rendered_length >= LONG_NAMED_ITEM_LIMIT
        for item in named_items
    )
    if _strict_majority(count=long_named_item_count, total=len(named_items)):
        return _LayoutDecision(style=LayoutStyle.EXPANDED, hard_expansion=False)

    dense_item_count: int = sum(
        item.rendered_length >= DENSE_ITEM_LENGTH
        for item in items
    )
    if _strict_majority(count=dense_item_count, total=len(items)):
        return _LayoutDecision(style=LayoutStyle.EXPANDED, hard_expansion=False)

    long_value_count: int = sum(
        item.value_length >= LONG_VALUE_LENGTH
        for item in items
    )
    if _strict_majority(count=long_value_count, total=len(items)):
        return _LayoutDecision(style=LayoutStyle.EXPANDED, hard_expansion=False)

    return _LayoutDecision(style=LayoutStyle.COMPACT, hard_expansion=False)


def decide_layout(items: tuple[LayoutItem, ...], compact_length: int, *, preserve: bool = False) -> LayoutStyle:
    """
    Select one deterministic layout from structural and density metadata.
    """
    return _layout_decision(items=items, compact_length=compact_length, preserve=preserve).style


def _compact_delimiters(kind: LayoutKind, items: tuple[LayoutItem, ...]) -> str:
    joined_items: str = ", ".join(item.text for item in items)
    if kind == LayoutKind.DICTIONARY:
        return "{}" if not items else f"{{ {joined_items} }}"
    if kind == LayoutKind.LIST:
        return f"[{joined_items}]"
    if kind == LayoutKind.SET:
        return f"{{{joined_items}}}"
    if kind == LayoutKind.TUPLE and len(items) == 1:
        return f"({joined_items},)"
    return f"({joined_items})"


def _expression_requires_expansion(source: str, lines: list[str], offsets: list[int], node: ast.expr) -> bool:
    if isinstance(node, ast.Starred):
        return True
    if isinstance(node, _HARD_COMPLEX_EXPRESSION_TYPES):
        return True

    if isinstance(node, _SUPPORTED_CONTAINER_TYPES):
        decision: _LayoutDecision | None = _intrinsic_expression_decision(source=source, lines=lines, offsets=offsets, node=node)
        if decision is None:
            return node.lineno != node.end_lineno
        if decision.style == LayoutStyle.PRESERVE:
            return node.lineno != node.end_lineno
        return decision.style == LayoutStyle.EXPANDED

    for descendant in ast.walk(node):
        if descendant is node:
            continue
        if isinstance(
            descendant,
            (
                *_SUPPORTED_CONTAINER_TYPES,
                *_HARD_COMPLEX_EXPRESSION_TYPES,
            ),
        ):
            return True

    return node.lineno != node.end_lineno


def _call_items(source: str, lines: list[str], offsets: list[int], node: ast.Call) -> tuple[LayoutItem, ...] | None:
    items: list[LayoutItem] = []

    for argument in node.args:
        argument_text: str | None = _normalized_node_text(source=source, lines=lines, offsets=offsets, node=argument)
        if argument_text is None:
            return None

        if isinstance(argument, ast.Starred):
            items.append(
                _layout_item(
                    argument_text,
                    value_length=max(
                        0,
                        len(argument_text) - 1,
                    ),
                    has_nested_structure=True,
                ),
            )
            continue

        items.append(
            _layout_item(
                argument_text,
                value_length=len(argument_text.replace("\n", "").replace("\r", "")),
                has_nested_structure=_expression_requires_expansion(source=source, lines=lines, offsets=offsets, node=argument),
            ),
        )

    for keyword in node.keywords:
        value_text: str | None = _normalized_node_text(source=source, lines=lines, offsets=offsets, node=keyword.value)
        if value_text is None:
            return None

        if keyword.arg is None:
            items.append(_layout_item(_unpacking_item_text(prefix="**", value_text=value_text, node=keyword.value), value_length=len(value_text), has_nested_structure=True))
            continue

        item_text: str = f"{keyword.arg}={value_text}"
        items.append(
            _layout_item(
                item_text,
                value_length=len(value_text.replace("\n", "").replace("\r", "")),
                name_length=len(keyword.arg),
                is_named=True,
                has_nested_structure=_expression_requires_expansion(source=source, lines=lines, offsets=offsets, node=keyword.value),
            ),
        )

    return tuple(items)


def _parameter_item(
    source: str,
    lines: list[str],
    offsets: list[int],
    parameter: ast.arg,
    default: ast.expr | None,
    prefix: str = "",
) -> LayoutItem | None:
    text: str = f"{prefix}{parameter.arg}"
    value_parts: list[str] = []

    if parameter.annotation is not None:
        annotation_text: str | None = _normalized_node_text(source=source, lines=lines, offsets=offsets, node=parameter.annotation)
        if annotation_text is None:
            return None
        text = f"{text}: {annotation_text}"
        value_parts.append(annotation_text)

    has_nested_structure: bool = False
    if default is not None:
        default_text: str | None = _normalized_node_text(source=source, lines=lines, offsets=offsets, node=default)
        if default_text is None:
            return None

        separator: str = " = " if parameter.annotation is not None else "="
        text = f"{text}{separator}{default_text}"
        value_parts.append(default_text)
        has_nested_structure = _expression_requires_expansion(source=source, lines=lines, offsets=offsets, node=default)

    value_length: int = sum(
        len(part.replace("\n", "").replace("\r", ""))
        for part in value_parts
    )
    return _layout_item(text, value_length=value_length, name_length=len(parameter.arg), is_named=True, has_nested_structure=has_nested_structure)


def _function_items(source: str, lines: list[str], offsets: list[int], node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[LayoutItem, ...] | None:
    items: list[LayoutItem] = []
    positional: list[ast.arg] = [
        *node.args.posonlyargs,
        *node.args.args,
    ]
    default_start: int = len(positional) - len(node.args.defaults)

    for index, parameter in enumerate(positional):
        default: ast.expr | None = (
            node.args.defaults[index - default_start]
            if index >= default_start
            else None
        )
        item: LayoutItem | None = _parameter_item(source=source, lines=lines, offsets=offsets, parameter=parameter, default=default)
        if item is None:
            return None
        items.append(item)

        if node.args.posonlyargs and index + 1 == len(node.args.posonlyargs):
            items.append(_layout_item("/"))

    if node.args.vararg is not None:
        item = _parameter_item(source=source, lines=lines, offsets=offsets, parameter=node.args.vararg, default=None, prefix="*")
        if item is None:
            return None
        items.append(item)
    elif node.args.kwonlyargs:
        items.append(_layout_item("*"))

    for parameter, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        item = _parameter_item(source=source, lines=lines, offsets=offsets, parameter=parameter, default=default)
        if item is None:
            return None
        items.append(item)

    if node.args.kwarg is not None:
        item = _parameter_item(source=source, lines=lines, offsets=offsets, parameter=node.args.kwarg, default=None, prefix="**")
        if item is None:
            return None
        items.append(item)

    return tuple(items)


def _dictionary_items(source: str, lines: list[str], offsets: list[int], node: ast.Dict) -> tuple[LayoutItem, ...] | None:
    items: list[LayoutItem] = []

    for key, value in zip(node.keys, node.values):
        value_text: str | None = _normalized_node_text(source=source, lines=lines, offsets=offsets, node=value)
        if value_text is None:
            return None

        if key is None:
            items.append(_layout_item(_unpacking_item_text(prefix="**", value_text=value_text, node=value), value_length=len(value_text), has_nested_structure=True))
            continue

        key_text: str | None = _normalized_node_text(source=source, lines=lines, offsets=offsets, node=key)
        if key_text is None:
            return None

        item_text: str = f"{key_text}: {value_text}"
        items.append(
            _layout_item(
                item_text,
                value_length=len(value_text.replace("\n", "").replace("\r", "")),
                name_length=len(key_text),
                is_named=True,
                has_nested_structure=(
                    _expression_requires_expansion(source=source, lines=lines, offsets=offsets, node=key)
                    or _expression_requires_expansion(source=source, lines=lines, offsets=offsets, node=value)
                ),
            ),
        )

    return tuple(items)


def _sequence_items(source: str, lines: list[str], offsets: list[int], node: ast.List | ast.Set | ast.Tuple) -> tuple[LayoutItem, ...] | None:
    items: list[LayoutItem] = []

    for element in node.elts:
        element_text: str | None = _normalized_node_text(source=source, lines=lines, offsets=offsets, node=element)
        if element_text is None:
            return None

        if isinstance(element, ast.Starred):
            items.append(
                _layout_item(
                    element_text,
                    value_length=max(
                        0,
                        len(element_text) - 1,
                    ),
                    has_nested_structure=True,
                ),
            )
            continue

        items.append(
            _layout_item(
                element_text,
                value_length=len(element_text.replace("\n", "").replace("\r", "")),
                has_nested_structure=_expression_requires_expansion(source=source, lines=lines, offsets=offsets, node=element),
            ),
        )

    return tuple(items)


def _intrinsic_expression_decision(source: str, lines: list[str], offsets: list[int], node: ast.expr) -> _LayoutDecision | None:
    segment: str | None = _normalized_node_text(source=source, lines=lines, offsets=offsets, node=node)
    if segment is None:
        return None

    preserve: bool = _contains_comment(segment=segment) or _contains_multiline_string(segment=segment)
    if preserve:
        return _LayoutDecision(style=LayoutStyle.PRESERVE, hard_expansion=False)

    kind: LayoutKind
    items: tuple[LayoutItem, ...] | None
    compact_prefix_length: int = 0

    if isinstance(node, ast.Call):
        kind = LayoutKind.CALL
        items = _call_items(source=source, lines=lines, offsets=offsets, node=node)
        function_text: str | None = _normalized_node_text(source=source, lines=lines, offsets=offsets, node=node.func)
        if function_text is None:
            return None
        compact_prefix_length = len(function_text)
    elif isinstance(node, ast.Dict):
        kind = LayoutKind.DICTIONARY
        items = _dictionary_items(source=source, lines=lines, offsets=offsets, node=node)
    elif isinstance(node, ast.List):
        kind = LayoutKind.LIST
        items = _sequence_items(source=source, lines=lines, offsets=offsets, node=node)
    elif isinstance(node, ast.Set):
        kind = LayoutKind.SET
        items = _sequence_items(source=source, lines=lines, offsets=offsets, node=node)
    elif isinstance(node, ast.Tuple):
        kind = LayoutKind.TUPLE
        items = _sequence_items(source=source, lines=lines, offsets=offsets, node=node)
    else:
        return None

    if items is None:
        return None

    compact_length: int = compact_prefix_length + len(_compact_delimiters(kind=kind, items=items))
    return _layout_decision(items=items, compact_length=compact_length)


def _matching_closer(tokens: list[_SourceToken], opener_index: int) -> int | None:
    pairs: dict[str, str] = { "(": ")", "[": "]", "{": "}" }
    opener: str = tokens[opener_index].token.string
    expected_closer: str | None = pairs.get(opener)
    if expected_closer is None:
        return None

    stack: list[str] = [expected_closer]
    for index in range(opener_index + 1, len(tokens)):
        token_string: str = tokens[index].token.string
        if token_string in pairs:
            stack.append(pairs[token_string])
            continue
        if stack and token_string == stack[-1]:
            stack.pop()
            if not stack:
                return index

    return None


def _expression_delimiters(
    source: str,
    lines: list[str],
    offsets: list[int],
    tokens: list[_SourceToken],
    node: ast.expr,
) -> tuple[int, int] | None:
    bounds: tuple[int, int] | None = _node_bounds(source=source, lines=lines, offsets=offsets, node=node)
    if bounds is None:
        return None
    node_start, node_end = bounds

    if isinstance(node, ast.Tuple):
        for index, source_token in enumerate(tokens):
            if source_token.start_offset != node_start or source_token.token.string != "(":
                continue
            closer_index: int | None = _matching_closer(tokens=tokens, opener_index=index)
            if closer_index is None:
                continue
            closer: _SourceToken = tokens[closer_index]
            return (index, closer_index) if closer.end_offset == node_end else None
        return None

    search_start: int = node_start
    if isinstance(node, ast.Call):
        function_bounds: tuple[int, int] | None = _node_bounds(source=source, lines=lines, offsets=offsets, node=node.func)
        if function_bounds is None:
            return None
        search_start = function_bounds[1]

    if isinstance(node, ast.Call):
        expected_opener: str = "("
    elif isinstance(node, ast.List):
        expected_opener = "["
    else:
        expected_opener = "{"

    for index, source_token in enumerate(tokens):
        if source_token.start_offset < search_start:
            continue
        if source_token.end_offset > node_end:
            break
        if source_token.token.string != expected_opener:
            continue

        closer_index: int | None = _matching_closer(tokens=tokens, opener_index=index)
        if closer_index is None:
            continue

        closer: _SourceToken = tokens[closer_index]
        if closer.end_offset == node_end:
            return index, closer_index

    return None


def _function_delimiters(tokens: list[_SourceToken], node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[int, int] | None:
    name_index: int | None = next(
        (
            index
            for index, source_token in enumerate(tokens)
            if source_token.token.start[0] == node.lineno
            and source_token.token.type == tokenize.NAME
            and source_token.token.string == node.name
        ),
        None,
    )
    if name_index is None:
        return None

    for index in range(name_index + 1, len(tokens)):
        if tokens[index].token.string != "(":
            continue
        closer_index: int | None = _matching_closer(tokens=tokens, opener_index=index)
        if closer_index is not None:
            return index, closer_index

    return None


def _has_trailing_comma(tokens: list[_SourceToken], opener_index: int, closer_index: int) -> bool:
    for index in range(closer_index - 1, opener_index, -1):
        token: tokenize.TokenInfo = tokens[index].token
        if token.type in _IGNORED_TRAILING_TOKEN_TYPES:
            continue
        return token.string == ","
    return False


def _compact_line_length(source: str, opener: _SourceToken, closer: _SourceToken, compact_delimiters: str) -> int:
    line_start_offset: int = opener.start_offset - opener.token.start[1]
    close_line_end: int = source.find("\n", closer.end_offset)
    if close_line_end == -1:
        close_line_end = len(source)

    prefix: str = source[line_start_offset:opener.start_offset]
    suffix: str = source[closer.end_offset:close_line_end].rstrip("\r")
    return len(prefix) + len(compact_delimiters) + len(suffix)


def _target(
    source: str,
    lines: list[str],
    tokens: list[_SourceToken],
    kind: LayoutKind,
    items: tuple[LayoutItem, ...],
    delimiter_indices: tuple[int, int],
    node: ast.AST,
) -> _LayoutTarget:
    opener_index, closer_index = delimiter_indices
    opener: _SourceToken = tokens[opener_index]
    closer: _SourceToken = tokens[closer_index]
    segment: str = source[opener.start_offset:closer.end_offset]

    compact_delimiters: str = _compact_delimiters(kind=kind, items=items)
    compact_length: int = _compact_line_length(source=source, opener=opener, closer=closer, compact_delimiters=compact_delimiters)

    preserve: bool = _contains_comment(segment=segment) or _contains_multiline_string(segment=segment)
    if kind == LayoutKind.CALL and len(items) == 1:
        preserve = preserve or (items[0].text.startswith("(") and " for " in items[0].text)

    actual_style: LayoutStyle = LayoutStyle.EXPANDED if opener.token.start[0] != closer.token.end[0] else LayoutStyle.COMPACT
    decision: _LayoutDecision = _layout_decision(items=items, compact_length=compact_length, preserve=preserve)

    line_text: str = lines[opener.token.start[0] - 1]
    base_indent: str = line_text[: len(line_text) - len(line_text.lstrip(" \t"))]

    return _LayoutTarget(
        context=LayoutContext(
            kind=kind,
            items=items,
            compact_length=compact_length,
            actual_style=actual_style,
            expected_style=decision.style,
            has_trailing_comma=_has_trailing_comma(tokens=tokens, opener_index=opener_index, closer_index=closer_index),
            line=opener.token.start[0],
            column=opener.token.start[1] + 1,
        ),
        start_offset=opener.start_offset,
        end_offset=closer.end_offset,
        opener=opener.token.string,
        closer=closer.token.string,
        base_indent=base_indent,
        node=node,
        hard_expansion=decision.hard_expansion,
    )


def _statement_blocks(tree: ast.Module) -> list[list[ast.stmt]]:
    blocks: list[list[ast.stmt]] = []

    for node in ast.walk(tree):
        for _, value in ast.iter_fields(node):
            if not isinstance(value, list) or not value:
                continue
            if all(isinstance(item, ast.stmt) for item in value):
                blocks.append(value)

    return blocks


def _call_statement(statement: ast.stmt) -> ast.Call | None:
    if not isinstance(statement, ast.Expr):
        return None

    value: ast.expr = statement.value.value if isinstance(statement.value, ast.Await) else statement.value
    return value if isinstance(value, ast.Call) else None


def _call_cohort_key(node: ast.Call) -> str:
    return ast.dump(node.func, annotate_fields=True, include_attributes=False)


def _cohort_runs(tree: ast.Module) -> list[list[ast.Call]]:
    runs: list[list[ast.Call]] = []

    for block in _statement_blocks(tree=tree):
        current_key: str | None = None
        current_run: list[ast.Call] = []

        def flush() -> None:
            nonlocal current_key, current_run
            if len(current_run) >= COHORT_MIN_SIZE:
                runs.append(current_run)
            current_key = None
            current_run = []

        for statement in block:
            call: ast.Call | None = _call_statement(statement=statement)
            if call is None:
                flush()
                continue

            key: str = _call_cohort_key(node=call)
            if current_key is not None and key != current_key:
                flush()

            if current_key is None:
                current_key = key
            current_run.append(call)

        flush()

    return runs


def _apply_call_cohort_consistency(tree: ast.Module, targets: list[_LayoutTarget]) -> list[_LayoutTarget]:
    target_indices_by_node: dict[int, int] = {
        id(target.node): index
        for index, target in enumerate(targets)
        if target.context.kind == LayoutKind.CALL
    }
    updated_targets: list[_LayoutTarget] = list(targets)

    for run in _cohort_runs(tree=tree):
        indices: list[int] = [
            target_indices_by_node[id(call)]
            for call in run
            if id(call) in target_indices_by_node
        ]
        if len(indices) < COHORT_MIN_SIZE:
            continue

        eligible_indices: list[int] = [
            index
            for index in indices
            if (
                not updated_targets[index].hard_expansion
                and updated_targets[index].context.expected_style in {LayoutStyle.COMPACT, LayoutStyle.EXPANDED}
            )
        ]
        if len(eligible_indices) < COHORT_MIN_SIZE:
            continue

        compact_count: int = sum(updated_targets[index].context.expected_style == LayoutStyle.COMPACT for index in eligible_indices)
        expanded_count: int = sum(updated_targets[index].context.expected_style == LayoutStyle.EXPANDED for index in eligible_indices)
        if compact_count == expanded_count:
            continue

        preferred_style: LayoutStyle = LayoutStyle.COMPACT if compact_count > expanded_count else LayoutStyle.EXPANDED
        for index in eligible_indices:
            target: _LayoutTarget = updated_targets[index]
            if target.context.expected_style == preferred_style:
                continue
            updated_targets[index] = replace(target, context=replace(target.context, expected_style=preferred_style))

    return updated_targets


def _layout_targets(source: str) -> list[_LayoutTarget]:
    tree: ast.Module = ast.parse(source, type_comments=True)
    lines, offsets = _line_offsets(source=source)
    tokens: list[_SourceToken] = _source_tokens(source=source, offsets=offsets)
    targets: list[_LayoutTarget] = []

    for node in ast.walk(tree):
        kind: LayoutKind
        items: tuple[LayoutItem, ...] | None
        delimiters: tuple[int, int] | None

        if isinstance(node, ast.Call):
            kind = LayoutKind.CALL
            items = _call_items(source=source, lines=lines, offsets=offsets, node=node)
            delimiters = _expression_delimiters(source=source, lines=lines, offsets=offsets, tokens=tokens, node=node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = LayoutKind.FUNCTION_DEFINITION
            items = _function_items(source=source, lines=lines, offsets=offsets, node=node)
            delimiters = _function_delimiters(tokens=tokens, node=node)
        elif isinstance(node, ast.Dict):
            kind = LayoutKind.DICTIONARY
            items = _dictionary_items(source=source, lines=lines, offsets=offsets, node=node)
            delimiters = _expression_delimiters(source=source, lines=lines, offsets=offsets, tokens=tokens, node=node)
        elif isinstance(node, ast.List):
            kind = LayoutKind.LIST
            items = _sequence_items(source=source, lines=lines, offsets=offsets, node=node)
            delimiters = _expression_delimiters(source=source, lines=lines, offsets=offsets, tokens=tokens, node=node)
        elif isinstance(node, ast.Set):
            kind = LayoutKind.SET
            items = _sequence_items(source=source, lines=lines, offsets=offsets, node=node)
            delimiters = _expression_delimiters(source=source, lines=lines, offsets=offsets, tokens=tokens, node=node)
        elif isinstance(node, ast.Tuple):
            kind = LayoutKind.TUPLE
            items = _sequence_items(source=source, lines=lines, offsets=offsets, node=node)
            delimiters = _expression_delimiters(source=source, lines=lines, offsets=offsets, tokens=tokens, node=node)
        else:
            continue

        if items is None or delimiters is None:
            continue

        targets.append(
            _target(
                source=source,
                lines=lines,
                tokens=tokens,
                kind=kind,
                items=items,
                delimiter_indices=delimiters,
                node=node,
            ),
        )

    return _apply_call_cohort_consistency(tree=tree, targets=targets)


def layout_contexts(source: str) -> tuple[LayoutContext, ...]:
    """
    Return every supported container's shared policy decision.
    """
    return tuple(
        target.context
        for target in _layout_targets(source=source)
    )


def _expanded_delimiters(source: str, target: _LayoutTarget) -> str:
    newline: str = "\r\n" if "\r\n" in source else "\n"
    item_indent: str = f"{target.base_indent}{_INDENT}"
    rendered_items: list[str] = []

    for item in target.context.items:
        item_lines: list[str] = item.text.splitlines()
        indented_lines: list[str] = [
            f"{item_indent}{line}"
            for line in item_lines
        ]
        indented_lines[-1] = f"{indented_lines[-1]},"
        rendered_items.append(newline.join(indented_lines))

    body: str = newline.join(rendered_items)
    return (
        f"{target.opener}{newline}"
        f"{body}{newline}"
        f"{target.base_indent}{target.closer}"
    )


def _replacement(source: str, target: _LayoutTarget) -> str | None:
    style: LayoutStyle = target.context.expected_style
    if style == LayoutStyle.PRESERVE:
        return None
    if style == LayoutStyle.COMPACT:
        return _compact_delimiters(kind=target.context.kind, items=target.context.items)
    if not target.context.items:
        return _compact_delimiters(kind=target.context.kind, items=target.context.items)
    return _expanded_delimiters(source=source, target=target)


def normalize_layout(source: str) -> str:
    """
    Apply the shared canonical layout to calls, definitions, dictionaries, and sequences.
    """
    current_source: str = source

    while True:
        candidates: list[tuple[int, int, str]] = []

        for target in _layout_targets(source=current_source):
            replacement: str | None = _replacement(source=current_source, target=target)
            if replacement is None:
                continue

            current_segment: str = current_source[target.start_offset:target.end_offset]
            if replacement == current_segment:
                continue

            candidates.append((target.start_offset, target.end_offset, replacement))

        if not candidates:
            return current_source

        selected: list[tuple[int, int, str]] = []
        for candidate in sorted(candidates, key=lambda item: (item[1] - item[0], item[0])):
            start_offset, end_offset, _ = candidate
            if any(
                start_offset < selected_end
                and selected_start < end_offset
                for selected_start, selected_end, _ in selected
            ):
                continue
            selected.append(candidate)

        for start_offset, end_offset, replacement in sorted(selected, key=lambda item: item[0], reverse=True):
            current_source = (
                f"{current_source[:start_offset]}"
                f"{replacement}"
                f"{current_source[end_offset:]}"
            )
