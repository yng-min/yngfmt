"""
Formatter engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

import autopep8

from yngfmt.imports import ImportConfig, sort_imports
from yngfmt.transforms import apply_custom_transforms


_MECHANICAL_FIXES: Final[tuple[str, ...]] = (
    "E1",
    "E2",
    "W291",
    "W292",
    "W293",
    "W391",
)


@dataclass(frozen=True, slots=True)
class FormatResult:
    """
    Represent the result of formatting one file.
    """
    path: Path
    changed: bool
    source: str


def _format_mechanical_whitespace(source: str) -> str:
    """
    Normalize mechanical whitespace without any line-length-based rewriting.
    """
    return autopep8.fix_code(
        source,
        options={ "select": list(_MECHANICAL_FIXES) },
        apply_config=False,
    )


def format_code(
    source: str,
    *,
    import_config: ImportConfig = ImportConfig(),
) -> str:
    """
    Format Python source according to the supported guide rules.
    """
    whitespace_formatted: str = _format_mechanical_whitespace(source=source)
    import_formatted: str = sort_imports(
        source=whitespace_formatted,
        config=import_config,
    )
    return apply_custom_transforms(source=import_formatted)


def format_path(
    path: Path,
    *,
    check: bool = False,
    import_config: ImportConfig = ImportConfig(),
) -> FormatResult:
    """
    Format one Python file and optionally write the result.
    """
    source: str = path.read_text(encoding="utf-8")
    formatted_source: str = format_code(
        source=source,
        import_config=import_config,
    )
    changed: bool = source != formatted_source

    if changed and not check:
        path.write_text(formatted_source, encoding="utf-8")

    return FormatResult(path=path, changed=changed, source=formatted_source)
