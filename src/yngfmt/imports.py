"""
Project-aware import sorting and checking.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
import ast
import sys
import tomllib


_KEEP_IMPORTS = "# yngfmt: keep-imports"
_OFF = "# yngfmt: off"
_ON = "# yngfmt: on"
_SKIP_FILE = "# yngfmt: skip-file"


@dataclass(frozen=True, slots=True)
class ImportConfig:
    """
    Configure project-aware import classification.
    """
    first_party: tuple[str, ...] = ()
    language_segment: str = "language"
    config_segment: str = "config"


@dataclass(frozen=True, slots=True)
class ImportRecord:
    """
    Represent one top-level import statement and its source text.
    """
    node: ast.Import | ast.ImportFrom
    text: str
    root: str
    module: str
    depth: int
    kind: int
    category: int
    segment: str
    original_index: int
    is_pinned: bool


@dataclass(frozen=True, slots=True)
class ImportIssue:
    """
    Describe an import ordering violation.
    """
    line: int
    column: int
    code: str
    message: str


def find_pyproject(start: Path) -> Path | None:
    """
    Find the nearest pyproject.toml from a file or directory.
    """
    current: Path = start if start.is_dir() else start.parent
    for directory in (current, *current.parents):
        candidate: Path = directory / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


def load_import_config(pyproject_path: Path | None) -> ImportConfig:
    """
    Load import settings from pyproject.toml.
    """
    if pyproject_path is None or not pyproject_path.is_file():
        return ImportConfig()

    data: dict[str, object] = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    tool_data: object = data.get("tool", {})
    settings: dict[str, object] = {}
    if isinstance(tool_data, dict):
        yngfmt_data: object = tool_data.get("yngfmt", {})
        if isinstance(yngfmt_data, dict):
            imports_data: object = yngfmt_data.get("imports", {})
            if isinstance(imports_data, dict):
                settings = imports_data

    first_party_value: object = settings.get("first-party", ())
    if isinstance(first_party_value, str):
        first_party: tuple[str, ...] = (first_party_value,)
    elif isinstance(first_party_value, (list, tuple)):
        first_party = tuple(
            item
            for item in first_party_value
            if isinstance(item, str)
        )
    else:
        first_party = ()

    language_segment_value: object = settings.get("language-segment", "language")
    config_segment_value: object = settings.get("config-segment", "config")
    language_segment: str = (
        language_segment_value if isinstance(language_segment_value, str) else "language"
    )
    config_segment: str = (
        config_segment_value if isinstance(config_segment_value, str) else "config"
    )
    return ImportConfig(
        first_party=first_party,
        language_segment=language_segment,
        config_segment=config_segment,
    )


def _module_name(node: ast.Import | ast.ImportFrom) -> str:
    if isinstance(node, ast.ImportFrom):
        return node.module or ""
    return node.names[0].name


def _root_name(node: ast.Import | ast.ImportFrom) -> str:
    module: str = _module_name(node=node)
    if isinstance(node, ast.ImportFrom) and node.level:
        return ""
    return module.split(".")[0]


def _segment_name(node: ast.Import | ast.ImportFrom, config: ImportConfig) -> str:
    module: str = _module_name(node=node)
    parts: list[str] = [part for part in module.split(".") if part]

    if isinstance(node, ast.ImportFrom) and node.level:
        return parts[0] if parts else ""
    if not parts or parts[0] not in config.first_party:
        return ""
    return parts[1] if len(parts) > 1 else ""


def _category(node: ast.Import | ast.ImportFrom, config: ImportConfig) -> int:
    if isinstance(node, ast.ImportFrom) and node.module == "__future__":
        return 0
    if isinstance(node, ast.ImportFrom) and node.level:
        return 3

    root: str = _root_name(node=node)
    if root in sys.stdlib_module_names:
        return 1
    if root in config.first_party:
        return 3
    return 2


def _kind(node: ast.Import | ast.ImportFrom) -> int:
    return 0 if isinstance(node, ast.ImportFrom) else 1


def _depth(node: ast.Import | ast.ImportFrom) -> int:
    module: str = _module_name(node=node)
    return len([part for part in module.split(".") if part])


def _segment_order(segment: str, config: ImportConfig) -> tuple[int, str]:
    if segment == config.language_segment:
        return 0, ""
    if segment == config.config_segment:
        return 2, ""
    return 1, segment.lower()


def _sort_key(record: ImportRecord, config: ImportConfig) -> tuple[object, ...]:
    segment_order: tuple[int, str] = _segment_order(
        segment=record.segment,
        config=config,
    )
    return (
        record.category,
        segment_order if record.category == 3 else (0, ""),
        record.kind,
        record.root.lower(),
        record.depth,
        record.module.lower(),
        record.text.lower(),
        record.original_index,
    )


def _top_level_import_nodes(tree: ast.Module) -> list[ast.Import | ast.ImportFrom]:
    nodes: list[ast.Import | ast.ImportFrom] = []
    body: list[ast.stmt] = tree.body
    start_index: int = 0

    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        start_index = 1

    for node in body[start_index:]:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            nodes.append(node)
            continue
        break
    return nodes


def _attached_start(lines: Sequence[str], start_line: int, lower_bound: int) -> int:
    current: int = start_line
    while current > lower_bound:
        previous: str = lines[current - 2]
        if not previous.lstrip().startswith("#"):
            break
        current -= 1
    return current


def _standalone_directive(line: str, directive: str) -> bool:
    return line.strip() == directive


def _attached_end(lines: Sequence[str], end_line: int) -> int:
    next_line: int = end_line + 1
    if next_line <= len(lines) and _standalone_directive(
        line=lines[next_line - 1],
        directive=_ON,
    ):
        return next_line
    return end_line


def _protected_lines(source: str) -> set[int]:
    lines: list[str] = source.splitlines()
    protected: set[int] = set()
    is_off: bool = False

    for index, line in enumerate(lines, start=1):
        if _standalone_directive(line=line, directive=_OFF):
            is_off = True
            protected.add(index)
            continue
        if _standalone_directive(line=line, directive=_ON):
            protected.add(index)
            is_off = False
            continue
        if is_off:
            protected.add(index)

        if _KEEP_IMPORTS not in line:
            continue

        prefix: str = line.split(_KEEP_IMPORTS, maxsplit=1)[0]
        if prefix.strip():
            protected.add(index)
            continue

        next_index: int = index + 1
        if next_index > len(lines) or not lines[next_index - 1].strip():
            continue

        current: int = next_index
        while current <= len(lines) and lines[current - 1].strip():
            protected.add(current)
            current += 1

    return protected


def _record_is_pinned(
    start_line: int,
    end_line: int,
    protected_lines: set[int],
) -> bool:
    return any(line in protected_lines for line in range(start_line, end_line + 1))


def _records(
    source: str,
    nodes: Sequence[ast.Import | ast.ImportFrom],
    config: ImportConfig,
    protected_lines: set[int],
) -> tuple[list[ImportRecord], int, int]:
    lines: list[str] = source.splitlines(keepends=True)
    records: list[ImportRecord] = []
    previous_end: int = 1
    final_end: int = nodes[-1].end_lineno or nodes[-1].lineno

    for index, node in enumerate(nodes):
        start_line: int = _attached_start(
            lines=lines,
            start_line=node.lineno,
            lower_bound=previous_end,
        )
        node_end: int = node.end_lineno or node.lineno
        end_line: int = _attached_end(lines=lines, end_line=node_end)
        text: str = "".join(lines[start_line - 1 : end_line]).strip("\n")
        records.append(
            ImportRecord(
                node=node,
                text=text,
                root=_root_name(node=node),
                module=_module_name(node=node),
                depth=_depth(node=node),
                kind=_kind(node=node),
                category=_category(node=node, config=config),
                segment=_segment_name(node=node, config=config),
                original_index=index,
                is_pinned=_record_is_pinned(
                    start_line=start_line,
                    end_line=end_line,
                    protected_lines=protected_lines,
                ),
            )
        )
        previous_end = end_line + 1
        final_end = end_line

    first_line: int = _attached_start(
        lines=lines,
        start_line=nodes[0].lineno,
        lower_bound=1,
    )
    return records, first_line, final_end


def _sort_with_pinned_records(
    records: Sequence[ImportRecord],
    config: ImportConfig,
) -> list[ImportRecord]:
    result: list[ImportRecord] = []
    pending: list[ImportRecord] = []

    for record in records:
        if not record.is_pinned:
            pending.append(record)
            continue

        result.extend(sorted(pending, key=lambda item: _sort_key(record=item, config=config)))
        pending.clear()
        result.append(record)

    result.extend(sorted(pending, key=lambda item: _sort_key(record=item, config=config)))
    return result


def _separator(
    previous: ImportRecord,
    current: ImportRecord,
    config: ImportConfig,
) -> str:
    if previous.is_pinned or current.is_pinned:
        return "\n"
    if previous.category != current.category:
        return "\n\n"
    if current.category != 3 or previous.segment == current.segment:
        return "\n"
    if current.segment == config.config_segment:
        return "\n\n\n"
    return "\n\n"


def _render(records: Sequence[ImportRecord], config: ImportConfig) -> str:
    if not records:
        return ""

    parts: list[str] = [records[0].text]
    for previous, current in zip(records, records[1:]):
        parts.append(_separator(previous=previous, current=current, config=config))
        parts.append(current.text)
    return "".join(parts)


def sort_imports(source: str, config: ImportConfig = ImportConfig()) -> str:
    """
    Sort the leading top-level import section according to the style guide.
    """
    if any(line.strip() == _SKIP_FILE for line in source.splitlines()):
        return source

    tree: ast.Module = ast.parse(source)
    nodes: list[ast.Import | ast.ImportFrom] = _top_level_import_nodes(tree=tree)
    if not nodes:
        return source

    protected_lines: set[int] = _protected_lines(source=source)
    records, first_line, last_line = _records(
        source=source,
        nodes=nodes,
        config=config,
        protected_lines=protected_lines,
    )
    sorted_records: list[ImportRecord] = _sort_with_pinned_records(
        records=records,
        config=config,
    )
    rendered: str = _render(records=sorted_records, config=config)

    lines: list[str] = source.splitlines(keepends=True)
    before: str = "".join(lines[: first_line - 1])
    after: str = "".join(lines[last_line:]).lstrip("\n")
    suffix: str = "\n\n\n" if after else "\n"
    return f"{before}{rendered}{suffix}{after}"


def check_imports(
    source: str,
    config: ImportConfig = ImportConfig(),
) -> list[ImportIssue]:
    """
    Return one diagnostic when the import section differs from canonical output.
    """
    try:
        formatted: str = sort_imports(source=source, config=config)
        tree: ast.Module = ast.parse(source)
    except SyntaxError:
        return []

    if formatted == source:
        return []

    nodes: list[ast.Import | ast.ImportFrom] = _top_level_import_nodes(tree=tree)
    line: int = nodes[0].lineno if nodes else 1
    return [
        ImportIssue(
            line=line,
            column=1,
            code="YNG400",
            message="import section does not match project import ordering rules",
        )
    ]
