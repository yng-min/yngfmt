"""
Command-line interface for the style guide linter.
"""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path

from yngfmt.imports import ImportConfig, find_pyproject, load_import_config

from yngfmt.linter import Diagnostic, ResultConfig, iter_python_files, lint_path, load_result_config


def build_parser() -> ArgumentParser:
    """
    Build the command-line parser.
    """
    parser: ArgumentParser = ArgumentParser(prog="ynglint")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument(
        "--pyproject",
        type=Path,
        help="Explicit pyproject.toml path for project checker settings.",
    )
    return parser


def main() -> int:
    """
    Run the linter and return a process exit code.
    """
    arguments: Namespace = build_parser().parse_args()
    files: list[Path] = list(
        iter_python_files(paths=arguments.paths),
    )
    pyproject_path: Path | None = arguments.pyproject
    if pyproject_path is None and files:
        pyproject_path = find_pyproject(files[0])

    import_config: ImportConfig = load_import_config(pyproject_path)
    result_config: ResultConfig = load_result_config(pyproject_path)

    diagnostics: list[Diagnostic] = []
    for path in files:
        diagnostics.extend(
            lint_path(path=path, import_config=import_config, result_config=result_config),
        )

    for diagnostic in diagnostics:
        print(
            diagnostic.render(),
        )
    return 1 if any(item.severity == "error" for item in diagnostics) else 0
