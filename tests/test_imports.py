"""
Tests for project-aware import sorting.
"""

from yngfmt.imports import ImportConfig, check_imports, sort_imports


CONFIG = ImportConfig(
    first_party=("project",),
)


def test_sorts_standard_and_third_party_imports() -> None:
    source = "import requests\nimport json\nfrom pathlib import Path\nfrom requests import Session\n"
    assert sort_imports(source=source, config=CONFIG) == (
        "from pathlib import Path\n"
        "import json\n"
        "\n"
        "from requests import Session\n"
        "import requests\n"
    )


def test_sorts_first_party_segments() -> None:
    source = (
        "from project.infrastructure.storage import Storage\n"
        "from project.config.runtime import runtime_config\n"
        "from project.domain.article import Article\n"
        "from project.language.i18n import translate\n"
        "from project.application.service import Service\n"
    )
    assert sort_imports(source=source, config=CONFIG) == (
        "from project.language.i18n import translate\n"
        "\n"
        "from project.application.service import Service\n"
        "\n"
        "from project.domain.article import Article\n"
        "\n"
        "from project.infrastructure.storage import Storage\n"
        "\n\n"
        "from project.config.runtime import runtime_config\n"
    )


def test_groups_each_first_party_segment_even_for_direct_modules() -> None:
    config = ImportConfig(
        first_party=("yngfmt",),
    )
    source = (
        "from yngfmt.transforms import apply_custom_transforms\n"
        "from yngfmt.imports import ImportConfig, sort_imports\n"
        "from yngfmt.formatter import format_code\n"
    )
    assert sort_imports(source=source, config=config) == (
        "from yngfmt.formatter import format_code\n"
        "\n"
        "from yngfmt.imports import ImportConfig, sort_imports\n"
        "\n"
        "from yngfmt.transforms import apply_custom_transforms\n"
    )


def test_groups_direct_module_with_nested_segment_imports() -> None:
    source = (
        "from project.domain.article import Article\n"
        "from project.domain import DomainService\n"
        "from project.application.service import Service\n"
    )
    assert sort_imports(source=source, config=CONFIG) == (
        "from project.application.service import Service\n"
        "\n"
        "from project.domain import DomainService\n"
        "from project.domain.article import Article\n"
    )


def test_keeps_body_separated_from_imports() -> None:
    source = "import json\n\nclass Service:\n    pass\n"
    assert sort_imports(source=source, config=CONFIG) == (
        "import json\n\n\nclass Service:\n    pass\n"
    )


def test_preserves_module_docstring() -> None:
    source = "\"\"\"Module.\"\"\"\n\nimport json\nfrom pathlib import Path\n"
    assert sort_imports(source=source, config=CONFIG) == (
        "\"\"\"Module.\"\"\"\n\n"
        "from pathlib import Path\n"
        "import json\n"
    )


def test_preserves_multiline_import_text() -> None:
    source = (
        "from package import (\n"
        "    B,\n"
        "    A,\n"
        ")\n"
        "from pathlib import Path\n"
    )
    assert sort_imports(source=source, config=CONFIG) == (
        "from pathlib import Path\n"
        "\n"
        "from package import (\n"
        "    B,\n"
        "    A,\n"
        ")\n"
    )


def test_keep_imports_standalone_directive_preserves_block() -> None:
    source = (
        "# yngfmt: keep-imports\n"
        "import plugin_b\n"
        "import plugin_a\n"
        "from pathlib import Path\n"
    )
    assert sort_imports(source=source, config=CONFIG) == (
        "# yngfmt: keep-imports\n"
        "import plugin_b\n"
        "import plugin_a\n"
        "from pathlib import Path\n"
    )


def test_keep_imports_inline_directive_pins_one_import() -> None:
    source = (
        "import requests\n"
        "import plugin_b # yngfmt: keep-imports\n"
        "import json\n"
        "from pathlib import Path\n"
    )
    assert sort_imports(source=source, config=CONFIG) == (
        "import requests\n"
        "import plugin_b # yngfmt: keep-imports\n"
        "from pathlib import Path\n"
        "import json\n"
    )


def test_off_on_directive_preserves_range() -> None:
    source = (
        "# yngfmt: off\n"
        "import plugin_b\n"
        "import plugin_a\n"
        "# yngfmt: on\n"
        "import json\n"
        "from pathlib import Path\n"
    )
    assert sort_imports(source=source, config=CONFIG) == (
        "# yngfmt: off\n"
        "import plugin_b\n"
        "import plugin_a\n"
        "# yngfmt: on\n"
        "from pathlib import Path\n"
        "import json\n"
    )


def test_skip_file_leaves_imports_untouched() -> None:
    source = "# yngfmt: skip-file\nimport json\nfrom pathlib import Path\n"
    assert sort_imports(source=source, config=CONFIG) == source


def test_check_imports_reports_noncanonical_section() -> None:
    source = "import json\nfrom pathlib import Path\n"
    issues = check_imports(source=source, config=CONFIG)
    assert [issue.code for issue in issues] == ["YNG400"]


def test_check_imports_accepts_canonical_section() -> None:
    source = "from pathlib import Path\nimport json\n"
    assert check_imports(source=source, config=CONFIG) == []
