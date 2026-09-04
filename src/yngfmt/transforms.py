"""
Custom syntax-preserving style transforms.
"""

from __future__ import annotations

from typing import Final, cast
import json

from libcst.metadata import CodeRange, MetadataWrapper, ParentNodeProvider, PositionProvider
import libcst as cst

from yngfmt.docstrings import compact_definition_docstring_spacing, normalize_docstring_delimiters

from yngfmt.layout_policy import normalize_layout

from yngfmt.structural_layout import compact_simple_calls, compact_thin_function_spacing


_CONTROL_CHARACTERS: Final[dict[str, str]] = {
    "\a": "\\a",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\v": "\\v",
}
_BYTE_CONTROL_CHARACTERS: Final[dict[int, str]] = {
    7: "\\a",
    8: "\\b",
    9: "\\t",
    10: "\\n",
    11: "\\v",
    12: "\\f",
    13: "\\r",
}
_TYPE_SUBSCRIPT_NAMES: Final[frozenset[str]] = frozenset(
    {"Annotated", "ClassVar", "Final", "Literal", "NotRequired", "Optional", "Required", "TypeGuard", "TypeIs", "Union", "dict", "frozenset", "list", "set", "tuple", "type"},
)


def _single_quoted_string(value: str) -> str:
    escaped_characters: list[str] = []
    for character in value:
        if character == "\\":
            escaped_characters.append("\\\\")
        elif character == "'":
            escaped_characters.append("\\'")
        elif character in _CONTROL_CHARACTERS:
            escaped_characters.append(_CONTROL_CHARACTERS[character])
        elif ord(character) < 32 or ord(character) == 127:
            escaped_characters.append(
                f"\\x{ord(character):02x}",
            )
        else:
            escaped_characters.append(character)

    return f"'{''.join(escaped_characters)}'"


def _double_quoted_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _double_quoted_bytes(value: bytes, prefix: str) -> str:
    escaped_characters: list[str] = []
    for byte in value:
        if byte == 92:
            escaped_characters.append("\\\\")
        elif byte == 34:
            escaped_characters.append("\\\"")
        elif byte in _BYTE_CONTROL_CHARACTERS:
            escaped_characters.append(_BYTE_CONTROL_CHARACTERS[byte])
        elif 32 <= byte < 127:
            escaped_characters.append(chr(byte))
        else:
            escaped_characters.append(f"\\x{byte:02x}")

    joined_characters: str = "".join(escaped_characters)
    return f"{prefix}\"{joined_characters}\""


def _has_odd_trailing_backslashes(value: str) -> bool:
    trailing_backslashes: int = len(value) - len(value.rstrip("\\"))
    return trailing_backslashes % 2 == 1


def _raw_double_quoted_string(value: str, prefix: str) -> str | None:
    if "\"" in value or _has_odd_trailing_backslashes(value=value):
        return None
    return f"{prefix}\"{value}\""


def _double_quoted_literal(node: cst.SimpleString) -> str | None:
    if node.quote in {"\"\"\"", "'''"} or node.quote == "\"":
        return None

    prefix: str = node.prefix
    normalized_prefix: str = prefix.casefold()
    evaluated_value: str | bytes = node.evaluated_value

    if "r" in normalized_prefix:
        if isinstance(evaluated_value, bytes):
            try:
                raw_value: str = evaluated_value.decode("ascii")
            except UnicodeDecodeError:
                return None
        else:
            raw_value = evaluated_value
        return _raw_double_quoted_string(value=raw_value, prefix=prefix)

    if isinstance(evaluated_value, bytes):
        return _double_quoted_bytes(value=evaluated_value, prefix=prefix)

    return f"{prefix}{_double_quoted_string(value=evaluated_value)}"


def _plain_string_value(node: cst.SimpleString) -> str | None:
    if node.prefix or node.quote in {"\"\"\"", "'''"}:
        return None

    evaluated_value: str | bytes = node.evaluated_value
    if not isinstance(evaluated_value, str):
        return None
    return evaluated_value


def _subscript_name(value: cst.BaseExpression) -> str | None:
    if isinstance(value, cst.Name):
        return value.value
    if isinstance(value, cst.Attribute):
        return value.attr.value
    return None


def _uses_dictionary_key_quote(node: cst.Subscript) -> bool:
    name: str | None = _subscript_name(value=node.value)
    if name is None:
        return True
    if name in _TYPE_SUBSCRIPT_NAMES:
        return False
    return not name[:1].isupper()


class YngminStyleTransformer(cst.CSTTransformer):
    """
    Apply rules that mechanical whitespace normalization cannot represent safely.
    """
    METADATA_DEPENDENCIES = (ParentNodeProvider, PositionProvider)

    def _inside_formatted_string(self, node: cst.CSTNode) -> bool:
        """
        Return whether a node belongs to an f-string expression.
        """
        current: cst.CSTNode = node
        while True:
            parent: cst.CSTNode | None = self.get_metadata(ParentNodeProvider, current, default=None)
            if parent is None:
                return False
            if isinstance(parent, cst.FormattedString):
                return True
            current = parent

    def leave_SimpleString(self, original_node: cst.SimpleString, updated_node: cst.SimpleString) -> cst.SimpleString:
        if self._inside_formatted_string(node=original_node):
            return updated_node

        value: str | None = _double_quoted_literal(node=original_node)
        if value is None:
            return updated_node
        return updated_node.with_changes(value=value)

    def leave_Subscript(self, original_node: cst.Subscript, updated_node: cst.Subscript) -> cst.Subscript:
        if not _uses_dictionary_key_quote(node=original_node):
            return updated_node

        updated_slices: list[cst.SubscriptElement] = []
        for slice_element in updated_node.slice:
            slice_value = slice_element.slice
            if not isinstance(slice_value, cst.Index):
                updated_slices.append(slice_element)
                continue

            string_node = slice_value.value
            if not isinstance(string_node, cst.SimpleString):
                updated_slices.append(slice_element)
                continue

            value: str | None = _plain_string_value(node=string_node)
            if value is None:
                updated_slices.append(slice_element)
                continue

            updated_string: cst.SimpleString = string_node.with_changes(value=_single_quoted_string(value=value))
            updated_index: cst.Index = slice_value.with_changes(value=updated_string)
            updated_slices.append(slice_element.with_changes(slice=updated_index))
        return updated_node.with_changes(slice=tuple(updated_slices))

    def leave_Dict(self, original_node: cst.Dict, updated_node: cst.Dict) -> cst.Dict:
        if not original_node.elements:
            return updated_node.with_changes(
                lbrace=updated_node.lbrace.with_changes(whitespace_after=cst.SimpleWhitespace("")),
                rbrace=updated_node.rbrace.with_changes(whitespace_before=cst.SimpleWhitespace("")),
            )

        position: CodeRange = cast(CodeRange, self.get_metadata(PositionProvider, original_node))
        if position.start.line != position.end.line:
            return updated_node

        return updated_node.with_changes(
            lbrace=updated_node.lbrace.with_changes(whitespace_after=cst.SimpleWhitespace(" ")),
            rbrace=updated_node.rbrace.with_changes(whitespace_before=cst.SimpleWhitespace(" ")),
        )

    def leave_TrailingWhitespace(
        self,
        original_node: cst.TrailingWhitespace,
        updated_node: cst.TrailingWhitespace,
    ) -> cst.TrailingWhitespace:
        if updated_node.comment is None:
            return updated_node
        return updated_node.with_changes(whitespace=cst.SimpleWhitespace(" "))


def apply_custom_transforms(source: str) -> str:
    """
    Apply syntax-aware custom formatting rules to source code.
    """
    module: cst.Module = cst.parse_module(source)
    wrapper: MetadataWrapper = MetadataWrapper(module)
    transformed_module: cst.Module = wrapper.visit(YngminStyleTransformer())
    docstrings_normalized: str = normalize_docstring_delimiters(source=transformed_module.code)
    docstring_spacing_compact: str = compact_definition_docstring_spacing(source=docstrings_normalized)
    call_chains_compact: str = compact_simple_calls(source=docstring_spacing_compact)
    layout_normalized: str = normalize_layout(source=call_chains_compact)
    return compact_thin_function_spacing(source=layout_normalized)
