"""
Custom syntax-preserving style transforms.
"""

from __future__ import annotations

import json
from typing import Final

import libcst as cst
from libcst.metadata import MetadataWrapper, PositionProvider


_CONTROL_CHARACTERS: Final[dict[str, str]] = {
    "\a": "\\a",
    "\b": "\\b",
    "\f": "\\f",
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\v": "\\v",
}


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
            escaped_characters.append(f"\\x{ord(character):02x}")
        else:
            escaped_characters.append(character)

    return f"'{''.join(escaped_characters)}'"


def _double_quoted_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _plain_string_value(node: cst.SimpleString) -> str | None:
    prefix = node.prefix.lower()
    if prefix or node.quote in {'"""', "'''"}:
        return None

    evaluated_value = node.evaluated_value
    if not isinstance(evaluated_value, str):
        return None

    return evaluated_value


class YngminStyleTransformer(cst.CSTTransformer):
    """
    Apply rules that Black cannot represent safely.
    """

    METADATA_DEPENDENCIES = (PositionProvider,)

    def leave_SimpleString(
        self,
        original_node: cst.SimpleString,
        updated_node: cst.SimpleString,
    ) -> cst.SimpleString:
        value = _plain_string_value(original_node)
        if value is None:
            return updated_node

        return updated_node.with_changes(value=_double_quoted_string(value))

    def leave_Subscript(
        self,
        original_node: cst.Subscript,
        updated_node: cst.Subscript,
    ) -> cst.Subscript:
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

            value = _plain_string_value(string_node)
            if value is None:
                updated_slices.append(slice_element)
                continue

            updated_string = string_node.with_changes(value=_single_quoted_string(value))
            updated_index = slice_value.with_changes(value=updated_string)
            updated_slices.append(slice_element.with_changes(slice=updated_index))
        return updated_node.with_changes(slice=tuple(updated_slices))

    def leave_Dict(
        self,
        original_node: cst.Dict,
        updated_node: cst.Dict,
    ) -> cst.Dict:
        if not original_node.elements:
            return updated_node.with_changes(
                lbrace=updated_node.lbrace.with_changes(
                    whitespace_after=cst.SimpleWhitespace("")
                ),
                rbrace=updated_node.rbrace.with_changes(
                    whitespace_before=cst.SimpleWhitespace("")
                ),
            )

        position = self.get_metadata(PositionProvider, original_node)
        if position.start.line != position.end.line:
            return updated_node

        return updated_node.with_changes(
            lbrace=updated_node.lbrace.with_changes(
                whitespace_after=cst.SimpleWhitespace(" ")
            ),
            rbrace=updated_node.rbrace.with_changes(
                whitespace_before=cst.SimpleWhitespace(" ")
            ),
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
    module = cst.parse_module(source)
    wrapper = MetadataWrapper(module)
    transformed_module = wrapper.visit(YngminStyleTransformer())
    return transformed_module.code
