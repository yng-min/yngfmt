"""
Style guide linter engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
import ast
import io
import re
import tokenize
import tomllib

from yngfmt.imports import ImportConfig, check_imports
from yngfmt.mechanical_rules import check_mechanical_rules


_SNAKE_CASE_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")
_PASCAL_CASE_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9]*$")
_FRAMEWORK_CALLBACK_SUFFIX_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9]*$")


@dataclass(frozen=True, slots=True)
class ResultConfig:
    """
    Configure result object detection and field validation.
    """
    class_names: tuple[str, ...] = ("Result",)
    typed_dict_names: tuple[str, ...] = ("ResultDict",)
    required_fields: tuple[str, ...] = ("error", "code", "message", "data")
    marker_fields: tuple[str, ...] = ("error", "code")
    aliases: tuple[str, ...] = ("success", "msg", "payload")


def load_result_config(pyproject_path: Path | None) -> ResultConfig:
    """
    Load result object settings from pyproject.toml.
    """
    if pyproject_path is None or not pyproject_path.is_file():
        return ResultConfig()

    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    settings = data.get("tool", {}).get("yngfmt", {}).get("result-object", {})

    def strings(key: str, default: tuple[str, ...]) -> tuple[str, ...]:
        value = settings.get(key, default)
        if isinstance(value, str):
            return (value,)
        return tuple(item for item in value if isinstance(item, str))

    return ResultConfig(
        class_names=strings("class-names", ResultConfig.class_names),
        typed_dict_names=strings("typed-dict-names", ResultConfig.typed_dict_names),
        required_fields=strings("required-fields", ResultConfig.required_fields),
        marker_fields=strings("marker-fields", ResultConfig.marker_fields),
        aliases=strings("aliases", ResultConfig.aliases),
    )


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """
    Describe one style guide violation.
    """
    path: Path
    line: int
    column: int
    code: str
    message: str
    severity: str = "error"

    def render(self) -> str:
        suffix: str = " [warning]" if self.severity == "warning" else ""
        return f"{self.path}:{self.line}:{self.column}: {self.code} {self.message}{suffix}"


def _base_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _framework_callback_prefixes(node: ast.ClassDef) -> tuple[str, ...]:
    base_names: set[str] = {
        base_name
        for base in node.bases
        if (base_name := _base_name(base)) is not None
    }
    if "CSTTransformer" in base_names:
        return "visit_", "leave_"
    if "NodeVisitor" in base_names or "NodeTransformer" in base_names:
        return ("visit_",)
    return ()


class StyleGuideVisitor(ast.NodeVisitor):
    """
    Check syntax-aware style guide rules.
    """
    def __init__(self, path: Path) -> None:
        self.path: Path = path
        self.diagnostics: list[Diagnostic] = []
        self._callback_prefix_stack: list[tuple[str, ...]] = []

    def add(
        self,
        node: ast.AST,
        code: str,
        message: str,
        severity: str = "error",
    ) -> None:
        self.diagnostics.append(Diagnostic(
            path=self.path,
            line=getattr(node, "lineno", 1),
            column=getattr(node, "col_offset", 0) + 1,
            code=code,
            message=message,
            severity=severity,
        ))

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if not _PASCAL_CASE_PATTERN.fullmatch(node.name):
            self.add(node=node, code="YNG201", message="class name must use PascalCase")

        self._callback_prefix_stack.append(_framework_callback_prefixes(node=node))
        self.generic_visit(node)
        self._callback_prefix_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node=node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node=node)
        self.generic_visit(node)

    def _is_framework_callback(self, name: str) -> bool:
        if not self._callback_prefix_stack:
            return False

        for prefix in self._callback_prefix_stack[-1]:
            if not name.startswith(prefix):
                continue
            suffix: str = name[len(prefix) :]
            return _FRAMEWORK_CALLBACK_SUFFIX_PATTERN.fullmatch(suffix) is not None
        return False

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if not _SNAKE_CASE_PATTERN.fullmatch(node.name) and not self._is_framework_callback(name=node.name):
            self.add(
                node=node,
                code="YNG202",
                message="function and method names must use snake_case",
            )

        arguments: list[ast.arg] = [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]
        for argument in arguments:
            if argument.arg in {"self", "cls"}:
                continue
            if argument.annotation is None:
                self.add(
                    node=argument,
                    code="YNG301",
                    message="parameter type annotation is missing",
                )

        if node.args.vararg is not None and node.args.vararg.annotation is None:
            self.add(
                node=node.args.vararg,
                code="YNG301",
                message="*args type annotation is missing",
            )
        if node.args.kwarg is not None and node.args.kwarg.annotation is None:
            self.add(
                node=node.args.kwarg,
                code="YNG301",
                message="**kwargs type annotation is missing",
            )
        if node.returns is None:
            self.add(node=node, code="YNG302", message="return type annotation is missing")


def _target_name(target: ast.expr) -> str | None:
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return None


def _annotation_name(node: ast.expr | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _annotation_name(node.value)
    return None


def _string_prefix_and_quote(token_value: str) -> tuple[str, str] | None:
    match: re.Match[str] | None = re.match(r"(?i)^([rubf]*)(\"\"\"|'{3}|\"|')", token_value)
    return None if match is None else (match.group(1), match.group(2))


def _is_docstring_statement(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def _docstring_positions(tree: ast.AST) -> set[tuple[int, int]]:
    positions: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if isinstance(body, list) and body and _is_docstring_statement(body[0]):
            positions.add((body[0].value.lineno, body[0].value.col_offset))
    return positions


def _subscript_string_positions(tree: ast.AST) -> set[tuple[int, int]]:
    return {
        (node.slice.lineno, node.slice.col_offset)
        for node in ast.walk(tree)
        if isinstance(node, ast.Subscript)
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    }


def _check_tokens(source: str, path: Path, tree: ast.AST) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    docstrings: set[tuple[int, int]] = _docstring_positions(tree)
    subscripts: set[tuple[int, int]] = _subscript_string_positions(tree)

    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.STRING:
            continue
        parsed: tuple[str, str] | None = _string_prefix_and_quote(token.string)
        if parsed is None:
            continue
        _, quote = parsed
        position: tuple[int, int] = token.start
        is_docstring: bool = position in docstrings
        if is_docstring and quote != '"""':
            diagnostics.append(Diagnostic(
                path=path,
                line=token.start[0],
                column=token.start[1] + 1,
                code="YNG102",
                message="docstring must use triple double quotes",
            ))
        elif not is_docstring and position not in subscripts and quote in {"'", "'''"}:
            diagnostics.append(Diagnostic(
                path=path,
                line=token.start[0],
                column=token.start[1] + 1,
                code="YNG101",
                message="string must use double quotes",
            ))

    for line_number, line in enumerate(source.splitlines(), start=1):
        if "\t" in line:
            diagnostics.append(Diagnostic(
                path=path,
                line=line_number,
                column=line.index("\t") + 1,
                code="YNG001",
                message="tabs are not allowed",
            ))
    return diagnostics


def _check_subscript_quotes(source: str, path: Path, tree: ast.AST) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    lines: list[str] = source.splitlines()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        slice_node: ast.expr = node.slice
        if not (
            isinstance(slice_node, ast.Constant)
            and isinstance(slice_node.value, str)
            and slice_node.lineno == slice_node.end_lineno
        ):
            continue
        segment: str = lines[slice_node.lineno - 1][slice_node.col_offset : slice_node.end_col_offset]
        if not segment.startswith("'"):
            diagnostics.append(Diagnostic(
                path=path,
                line=slice_node.lineno,
                column=slice_node.col_offset + 1,
                code="YNG103",
                message="dictionary key access must use single quotes",
            ))
    return diagnostics


def _blank_lines_between(previous: ast.AST, current: ast.AST) -> int:
    previous_end: int = getattr(previous, "end_lineno", getattr(previous, "lineno", 1))
    current_start: int = getattr(current, "lineno", previous_end + 1)
    return max(0, current_start - previous_end - 1)


def _first_code_line(node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    return min((item.lineno for item in node.decorator_list), default=node.lineno)


def _check_docstring_layout(tree: ast.Module, path: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    if tree.body and _is_docstring_statement(tree.body[0]) and len(tree.body) > 1:
        docstring: ast.stmt = tree.body[0]
        if _blank_lines_between(docstring, tree.body[1]) != 1:
            diagnostics.append(Diagnostic(
                path=path,
                line=docstring.lineno,
                column=docstring.col_offset + 1,
                code="YNG104",
                message="module docstring must be followed by exactly one blank line",
            ))

    for node in ast.walk(tree):
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.body or not _is_docstring_statement(node.body[0]) or len(node.body) == 1:
            continue

        next_statement: ast.stmt = node.body[1]
        if isinstance(node, ast.ClassDef) and not isinstance(next_statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if _blank_lines_between(node.body[0], next_statement) == 0:
            continue

        code: str = "YNG105" if isinstance(node, ast.ClassDef) else "YNG106"
        subject: str = "class" if isinstance(node, ast.ClassDef) else "function"
        diagnostics.append(Diagnostic(
            path=path,
            line=next_statement.lineno,
            column=next_statement.col_offset + 1,
            code=code,
            message=f"{subject} docstring must not be followed by a blank line",
        ))
    return diagnostics


def _definition_header_end_line(
    source: str,
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
) -> int:
    fragment: str = "".join(source.splitlines(keepends=True)[node.lineno - 1 :])
    depth: int = 0
    for token in tokenize.generate_tokens(io.StringIO(fragment).readline):
        if token.type != tokenize.OP:
            continue
        if token.string in {"(", "[", "{"}:
            depth += 1
        elif token.string in {")", "]", "}"}:
            depth -= 1
        elif token.string == ":" and depth == 0:
            return node.lineno + token.end[0] - 1
    return node.lineno


def _check_definition_spacing(
    source: str,
    tree: ast.Module,
    path: Path,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    definitions: tuple[type[ast.ClassDef], type[ast.FunctionDef], type[ast.AsyncFunctionDef]] = (
        ast.ClassDef,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
    )
    has_seen_definition: bool = False

    for index, current in enumerate(tree.body):
        if not isinstance(current, definitions):
            continue
        if not has_seen_definition:
            has_seen_definition = True
            continue

        previous: ast.stmt = tree.body[index - 1]
        previous_end: int = previous.end_lineno or previous.lineno
        if _first_code_line(current) - previous_end - 1 != 2:
            diagnostics.append(Diagnostic(
                path=path,
                line=_first_code_line(current),
                column=1,
                code="YNG401",
                message="top-level definition must be preceded by two blank lines",
            ))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            header_end: int = _definition_header_end_line(source=source, node=node)
            if node.body[0].lineno - header_end - 1 > 0:
                diagnostics.append(Diagnostic(
                    path=path,
                    line=node.body[0].lineno,
                    column=node.body[0].col_offset + 1,
                    code="YNG403",
                    message="function body must start immediately after the declaration",
                ))

    for class_node in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
        body: list[ast.stmt] = class_node.body
        start: int = 1 if body and _is_docstring_statement(body[0]) else 0
        methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = [
            node
            for node in body[start:]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        for previous, current in zip(methods, methods[1:]):
            previous_end: int = previous.end_lineno or previous.lineno
            if _first_code_line(current) - previous_end - 1 != 1:
                diagnostics.append(Diagnostic(
                    path=path,
                    line=_first_code_line(current),
                    column=current.col_offset + 1,
                    code="YNG402",
                    message="class methods must be separated by one blank line",
                ))
    return diagnostics


def _body_without_docstring(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.stmt]:
    return node.body[1:] if node.body and _is_docstring_statement(node.body[0]) else node.body


def _is_call_statement(node: ast.stmt) -> bool:
    if not isinstance(node, ast.Expr):
        return False
    value: ast.expr = node.value.value if isinstance(node.value, ast.Await) else node.value
    return isinstance(value, ast.Call)


def _check_wrapper_and_return_spacing(tree: ast.Module, path: Path) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body: list[ast.stmt] = _body_without_docstring(node=node)
        if (
            len(body) == 2
            and _is_call_statement(body[0])
            and isinstance(body[1], ast.Return)
            and _blank_lines_between(body[0], body[1]) > 0
        ):
            diagnostics.append(Diagnostic(
                path=path,
                line=body[1].lineno,
                column=body[1].col_offset + 1,
                code="YNG501",
                message="short wrapper preparation and delegation must remain adjacent",
            ))

        for previous, current in zip(body, body[1:]):
            if not isinstance(current, ast.Return) or _blank_lines_between(previous, current) == 0:
                continue
            target: ast.expr | None = (
                previous.targets[0]
                if isinstance(previous, ast.Assign)
                else previous.target
                if isinstance(previous, ast.AnnAssign)
                else None
            )
            target_name: str | None = _target_name(target) if target is not None else None
            if target_name is not None and isinstance(current.value, ast.Name) and current.value.id == target_name:
                diagnostics.append(Diagnostic(
                    path=path,
                    line=current.lineno,
                    column=current.col_offset + 1,
                    code="YNG502",
                    message="return must remain adjacent to the statement producing its value",
                ))
    return diagnostics


def _dictionary_string_keys(node: ast.Dict) -> set[str] | None:
    keys: set[str] = set()
    for key in node.keys:
        if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
            return None
        keys.add(key.value)
    return keys


def _typed_dict_fields(node: ast.ClassDef) -> set[str]:
    return {
        statement.target.id
        for statement in node.body
        if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name)
    }


def _is_typed_dict(node: ast.ClassDef) -> bool:
    return any(_annotation_name(base) == "TypedDict" for base in node.bases)


def _assignment_dicts(
    function: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, ast.Dict]:
    assignments: dict[str, ast.Dict] = {}
    invalidated: set[str] = set()
    for node in ast.walk(function):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            name: str = node.targets[0].id
            if name in assignments:
                invalidated.add(name)
            if isinstance(node.value, ast.Dict):
                assignments[name] = node.value
            else:
                invalidated.add(name)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            name = node.target.id
            if name in assignments:
                invalidated.add(name)
            if isinstance(node.value, ast.Dict):
                assignments[name] = node.value
            elif node.value is not None:
                invalidated.add(name)
        elif isinstance(node, (ast.AugAssign, ast.NamedExpr)) and isinstance(node.target, ast.Name):
            invalidated.add(node.target.id)
    return {name: value for name, value in assignments.items() if name not in invalidated}


def _result_candidate(
    keys: set[str],
    config: ResultConfig,
    forced: bool = False,
) -> bool:
    return forced or bool(keys & set(config.marker_fields)) or bool(keys & set(config.aliases))


def _validate_result_keys(
    keys: set[str],
    node: ast.stmt,
    path: Path,
    config: ResultConfig,
) -> list[Diagnostic]:
    aliases: list[str] = sorted(keys & set(config.aliases))
    if aliases:
        return [Diagnostic(
            path=path,
            line=node.lineno,
            column=node.col_offset + 1,
            code="YNG602",
            message=f"result dictionary uses non-standard field names: {', '.join(aliases)}",
        )]

    missing: list[str] = sorted(set(config.required_fields) - keys)
    if missing:
        return [Diagnostic(
            path=path,
            line=node.lineno,
            column=node.col_offset + 1,
            code="YNG601",
            message=f"result object is missing required fields: {', '.join(missing)}",
        )]
    return []


def _check_result_objects(
    tree: ast.Module,
    path: Path,
    config: ResultConfig,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    result_type_names: set[str] = set(config.class_names) | set(config.typed_dict_names)

    for node in tree.body:
        if (
            isinstance(node, ast.ClassDef)
            and node.name in config.typed_dict_names
            and _is_typed_dict(node)
        ):
            diagnostics.extend(_validate_result_keys(
                keys=_typed_dict_fields(node),
                node=node,
                path=path,
                config=config,
            ))

    for function in (
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ):
        assigned: dict[str, ast.Dict] = _assignment_dicts(function=function)
        forced: bool = _annotation_name(function.returns) in result_type_names
        returns: list[tuple[ast.Return, set[str]]] = []

        for node in ast.walk(function):
            if not isinstance(node, ast.Return):
                continue
            dictionary: ast.Dict | None = None
            if isinstance(node.value, ast.Dict):
                dictionary = node.value
            elif isinstance(node.value, ast.Name):
                dictionary = assigned.get(node.value.id)
            if dictionary is None:
                continue

            keys: set[str] | None = _dictionary_string_keys(dictionary)
            if keys is None or not _result_candidate(keys=keys, config=config, forced=forced):
                continue
            diagnostics.extend(_validate_result_keys(
                keys=keys,
                node=node,
                path=path,
                config=config,
            ))
            returns.append((node, keys))

        if len({frozenset(keys) for _, keys in returns}) > 1:
            baseline: set[str] = returns[0][1]
            for node, keys in returns[1:]:
                if keys != baseline:
                    diagnostics.append(Diagnostic(
                        path=path,
                        line=node.lineno,
                        column=node.col_offset + 1,
                        code="YNG603",
                        message="result return branches must use the same field set",
                    ))
    return diagnostics


def lint_code(
    source: str,
    path: Path = Path("<string>"),
    import_config: ImportConfig = ImportConfig(),
    result_config: ResultConfig = ResultConfig(),
) -> list[Diagnostic]:
    """
    Lint Python source and return sorted diagnostics.
    """
    try:
        tree: ast.Module = ast.parse(source)
    except SyntaxError as error:
        return [Diagnostic(path, error.lineno or 1, error.offset or 1, "YNG000", error.msg)]

    visitor: StyleGuideVisitor = StyleGuideVisitor(path)
    visitor.visit(tree)
    import_diagnostics: list[Diagnostic] = [
        Diagnostic(path, issue.line, issue.column, issue.code, issue.message)
        for issue in check_imports(source=source, config=import_config)
    ]
    mechanical_diagnostics: list[Diagnostic] = [
        Diagnostic(
            path=path,
            line=issue.line,
            column=issue.column,
            code=issue.code,
            message=issue.message,
        )
        for issue in check_mechanical_rules(source=source, tree=tree)
    ]
    diagnostics: list[Diagnostic] = [
        *visitor.diagnostics,
        *_check_tokens(source=source, path=path, tree=tree),
        *_check_subscript_quotes(source=source, path=path, tree=tree),
        *_check_docstring_layout(tree=tree, path=path),
        *_check_definition_spacing(source=source, tree=tree, path=path),
        *_check_wrapper_and_return_spacing(tree=tree, path=path),
        *_check_result_objects(tree=tree, path=path, config=result_config),
        *mechanical_diagnostics,
        *import_diagnostics,
    ]
    return sorted(diagnostics, key=lambda item: (item.line, item.column, item.code))


def iter_python_files(paths: Sequence[Path]) -> Iterable[Path]:
    """
    Yield Python files from files and directories.
    """
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            yield path
        elif path.is_dir():
            yield from sorted(path.rglob("*.py"))


def lint_path(
    path: Path,
    import_config: ImportConfig = ImportConfig(),
    result_config: ResultConfig = ResultConfig(),
) -> list[Diagnostic]:
    """
    Lint one Python file.
    """
    return lint_code(
        source=path.read_text(encoding="utf-8"),
        path=path,
        import_config=import_config,
        result_config=result_config,
    )
