"""
Command-line interface for yngfmt.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from pathlib import Path

from yngfmt.formatter import format_path
from yngfmt.imports import find_pyproject, load_import_config


def _python_files(paths: Iterable[Path]) -> list[Path]:
    resolved_files: set[Path] = set()
    for path in paths:
        if path.is_dir():
            resolved_files.update(
                candidate
                for candidate in path.rglob("*.py")
                if not any(part.startswith(".") for part in candidate.parts)
            )
        elif path.suffix == ".py":
            resolved_files.add(path)
    return sorted(resolved_files)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="yngfmt",
        description="Format Python code using yngmin's Python Style Guide."
    )
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write files and return a non-zero status when changes are needed."
    )
    parser.add_argument(
        "--line-length",
        default=88,
        type=int,
        help="Black line length used for the base formatting pass."
    )
    parser.add_argument(
        "--pyproject",
        type=Path,
        help="Explicit pyproject.toml path for project import settings."
    )
    return parser


def main() -> int:
    parser = _build_parser()
    arguments = parser.parse_args()
    files = _python_files(arguments.paths)
    if not files:
        parser.error("No Python files found")

    pyproject_path = arguments.pyproject or find_pyproject(files[0])
    import_config = load_import_config(pyproject_path)

    changed_files: list[Path] = []
    for path in files:
        result = format_path(
            path,
            check=arguments.check,
            line_length=arguments.line_length,
            import_config=import_config
        )
        if result.changed:
            changed_files.append(path)
            action = "would reformat" if arguments.check else "reformatted"
            print(f"{action} {path}")

    unchanged_count = len(files) - len(changed_files)
    print(
        f"{len(changed_files)} file(s) changed, "
        f"{unchanged_count} file(s) left unchanged"
    )
    return 1 if arguments.check and changed_files else 0


if __name__ == "__main__":
    raise SystemExit(main())
