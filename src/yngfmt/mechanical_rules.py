"""
Deterministic style-guide checks that should not rewrite source semantics.
"""

from dataclasses import dataclass
from typing import Final
import ast
import io
import re
import tokenize


_SIMPLE_CALL_ARGUMENT_TYPES: Final[tuple[type[ast.expr], ...]] = (
    ast.Attribute,
    ast.Constant,
    ast.JoinedStr,
    ast.Name,
)
_IGNORED_CALL_TOKEN_TYPES: Final[frozenset[int]] = frozenset({
    tokenize.COMMENT,
    tokenize.DEDENT,
    tokenize.ENDMARKER,
    tokenize.INDENT,
    tokenize.NEWLINE,
    tokenize.NL,
})
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
        if not isinstance(
            node,
            (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue

        docstring_value: ast.Constant | None = _docstring_value(body=node.body)
        if docstring_value is not None:
            positions.add((docstring_value.lineno, docstring_value.col_offset))
    return positions


def _string_prefix_and_quote(token_value: str) -> tuple[str, str] | None:
    match: re.Match[str] | None = re.match(
        r"(?i)^([rubf]*)(\"\"\"|'{3}|\"|')",
        token_value,
    )
    if match is None:
        return None
    return match.group(1), match.group(2)


def _check_docstring_delimiter_layout(
    source: str,
    tree: ast.Module,
) -> list[MechanicalIssue]:
    positions: set[tuple[int, int]] = _docstring_positions(tree=tree)
    diagnostics: list[MechanicalIssue] = []

    for token in tokenize.generate_tokens(io.StringIO(source).readline):
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
            diagnostics.append(MechanicalIssue(
                line=token.start[0],
                column=token.start[1] + 1,
                code="YNG107",
                message="docstring content must start on the line after opening quotes",
            ))
        if _DOCSTRING_CLOSING_LINE_PATTERN.search(body) is None:
            diagnostics.append(MechanicalIssue(
                line=token.end[0],
                column=max(1, token.end[1] - 2),
                code="YNG108",
                message="docstring closing quotes must be on their own line",
            ))
    return diagnostics


def _check_dictionary_spacing(
    source: str,
    tree: ast.Module,
) -> list[MechanicalIssue]:
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

        diagnostics.append(MechanicalIssue(
            line=node.lineno,
            column=node.col_offset + 1,
            code="YNG109",
            message="single-line dictionary literal has non-canonical inner spacing",
        ))
    return diagnostics


def _call_source_segment(source: str, node: ast.Call) -> str | None:
    return ast.get_source_segment(source, node)


def _significant_call_tokens(segment: str) -> tuple[tokenize.TokenInfo, ...]:
    return tuple(
        token
        for token in tokenize.generate_tokens(io.StringIO(segment).readline)
        if token.type not in _IGNORED_CALL_TOKEN_TYPES
    )


def _call_has_trailing_comma(segment: str) -> bool:
    tokens: tuple[tokenize.TokenInfo, ...] = _significant_call_tokens(segment=segment)
    if len(tokens) < 2 or tokens[-1].string != ")":
        return False
    return tokens[-2].string == ","


def _call_has_comment(segment: str) -> bool:
    return any(
        token.type == tokenize.COMMENT
        for token in tokenize.generate_tokens(io.StringIO(segment).readline)
    )


def _generator_only_call(node: ast.Call) -> bool:
    return (
        len(node.args) == 1
        and not node.keywords
        and isinstance(node.args[0], ast.GeneratorExp)
    )


def _single_simple_argument(node: ast.Call) -> ast.expr | None:
    argument_count: int = len(node.args) + len(node.keywords)
    if argument_count != 1:
        return None

    if node.args:
        argument: ast.expr = node.args[0]
        if isinstance(argument, ast.Starred):
            return None
        return argument

    keyword: ast.keyword = node.keywords[0]
    if keyword.arg is None:
        return None
    return keyword.value


def _outer_call_is_expanded(node: ast.Call) -> bool:
    """
    Return whether top-level call arguments start on lines after the callable.
    """
    function_end_line: int = node.func.end_lineno or node.func.lineno
    argument_lines: tuple[int, ...] = (
        *(argument.lineno for argument in node.args),
        *(keyword.value.lineno for keyword in node.keywords),
    )
    return any(line > function_end_line for line in argument_lines)


def _check_call_formatting(
    source: str,
    tree: ast.Module,
) -> list[MechanicalIssue]:
    diagnostics: list[MechanicalIssue] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        segment: str | None = _call_source_segment(source=source, node=node)
        if segment is None:
            continue

        argument_count: int = len(node.args) + len(node.keywords)
        is_multiline: bool = node.lineno != node.end_lineno
        has_trailing_comma: bool = _call_has_trailing_comma(segment=segment)
        outer_expanded: bool = _outer_call_is_expanded(node=node)

        if not is_multiline:
            if argument_count > 0 and has_trailing_comma:
                diagnostics.append(MechanicalIssue(
                    line=node.lineno,
                    column=node.col_offset + 1,
                    code="YNG703",
                    message="compact outer call must not use a trailing comma",
                ))
            continue

        if argument_count == 0:
            diagnostics.append(MechanicalIssue(
                line=node.lineno,
                column=node.col_offset + 1,
                code="YNG704",
                message="zero-argument call must stay on one line",
            ))
            continue

        if outer_expanded:
            if not _generator_only_call(node=node) and not has_trailing_comma:
                diagnostics.append(MechanicalIssue(
                    line=node.end_lineno or node.lineno,
                    column=node.end_col_offset or node.col_offset + 1,
                    code="YNG702",
                    message="expanded outer call must end its final argument with a trailing comma",
                ))
        elif has_trailing_comma:
            diagnostics.append(MechanicalIssue(
                line=node.end_lineno or node.lineno,
                column=node.end_col_offset or node.col_offset + 1,
                code="YNG703",
                message="compact outer call must not use a trailing comma",
            ))

        argument: ast.expr | None = _single_simple_argument(node=node)
        if argument is None:
            continue
        if not isinstance(argument, _SIMPLE_CALL_ARGUMENT_TYPES):
            continue
        if argument.lineno != argument.end_lineno or node.func.lineno != node.func.end_lineno:
            continue
        if _call_has_comment(segment=segment):
            continue

        diagnostics.append(MechanicalIssue(
            line=node.lineno,
            column=node.col_offset + 1,
            code="YNG701",
            message="simple single-argument call must stay on one line",
        ))
    return diagnostics


def check_mechanical_rules(
    source: str,
    tree: ast.Module,
) -> list[MechanicalIssue]:
    """
    Return deterministic style-guide violations not owned by the import sorter.
    """
    diagnostics: list[MechanicalIssue] = [
        *_check_docstring_delimiter_layout(source=source, tree=tree),
        *_check_dictionary_spacing(source=source, tree=tree),
        *_check_call_formatting(source=source, tree=tree),
    ]
    return diagnostics
