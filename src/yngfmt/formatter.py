"""
Formatter engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from black.report import NothingChanged
import black

from yngfmt.imports import ImportConfig, sort_imports
from yngfmt.transforms import apply_custom_transforms


@dataclass(frozen=True, slots=True)
class FormatResult:
    """
    Represent the result of formatting one file.
    """
    path: Path
    changed: bool
    source: str


def format_code(
    source: str,
    *,
    line_length: int = 88,
    import_config: ImportConfig = ImportConfig(),
) -> str:
    """
    Format Python source according to the supported guide rules.
    """
    mode: black.Mode = black.Mode(line_length=line_length, string_normalization=True)
    try:
        black_formatted: str = black.format_file_contents(
            source,
            fast=False,
            mode=mode,
        )
    except NothingChanged:
        black_formatted = source

    import_formatted: str = sort_imports(
        source=black_formatted,
        config=import_config,
    )
    return apply_custom_transforms(source=import_formatted)


def format_path(
    path: Path,
    *,
    check: bool = False,
    line_length: int = 88,
    import_config: ImportConfig = ImportConfig(),
) -> FormatResult:
    """
    Format one Python file and optionally write the result.
    """
    source: str = path.read_text(encoding="utf-8")
    formatted_source: str = format_code(
        source=source,
        line_length=line_length,
        import_config=import_config,
    )
    changed: bool = source != formatted_source

    if changed and not check:
        path.write_text(formatted_source, encoding="utf-8")

    return FormatResult(path=path, changed=changed, source=formatted_source)
