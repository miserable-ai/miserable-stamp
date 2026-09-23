"""Stamping `@id` markers into Python docstrings.

A function or class whose docstring carries `@relation(...)` or `@model(...)` but no `@id` gets
`@id c-...` as the last marker line of that docstring, indented like the marker before it. When the
closing quotes sit on that marker's line, they move to the end of the new line. Files that do not
parse are left untouched.
"""

import random
import re
from dataclasses import dataclass

import tree_sitter_python as tsp
from tree_sitter import Language, Node, Parser

from miserable_stamp.ids import new_code_id

_PARSER = Parser(Language(tsp.language()))
_DEFINITIONS = ("function_definition", "class_definition")
_PREFIX = r"[ \t]*(?:///|\*|#)?[ \t]*"
_LINKING_MARKER = re.compile(_PREFIX + r"@(?:relation|model)\(")
_ID_MARKER = re.compile(_PREFIX + r"@id\s+(c-[0-9a-hjkmnp-tv-z]{10})")


@dataclass(frozen=True)
class _Edit:
    line: int  # 0-based line of the last marker
    closing_on_line: bool  # the closing quotes are on that line
    closing_column: int  # byte column of the closing quotes, when on that line
    prefix: str  # indentation (and comment prefix) for the new line


def stamp_python(text: str, rng: random.Random) -> str:
    src = text.encode("utf-8")
    tree = _PARSER.parse(src)
    if tree.root_node.has_error:
        return text
    taken = {m.group(1) for m in _ID_MARKER.finditer(text)}
    edits = [e for d in _docstrings(tree.root_node) if (e := _plan(d, src)) is not None]
    lines = text.splitlines(keepends=True)
    for edit in sorted(edits, key=lambda e: e.line, reverse=True):
        new_id = new_code_id(rng, taken)
        line = lines[edit.line]
        if edit.closing_on_line:
            raw = line.encode("utf-8")
            before = raw[: edit.closing_column].decode("utf-8").rstrip()
            after = raw[edit.closing_column :].decode("utf-8")
            newline = "\r\n" if line.endswith("\r\n") else "\n"
            lines[edit.line] = before + newline
            lines.insert(edit.line + 1, f"{edit.prefix}@id {new_id}{after}")
        else:
            newline = "\r\n" if line.endswith("\r\n") else "\n"
            lines.insert(edit.line + 1, f"{edit.prefix}@id {new_id}{newline}")
    return "".join(lines)


def _docstrings(root: Node) -> list[Node]:
    """The docstring string node of every function and class, at any depth."""
    found: list[Node] = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type in _DEFINITIONS:
            body = node.child_by_field_name("body")
            if body is not None and body.named_child_count:
                first = body.named_children[0]
                if (
                    first.type == "expression_statement"
                    and first.named_child_count == 1
                    and first.named_children[0].type == "string"
                ):
                    found.append(first.named_children[0])
        stack.extend(node.children)
    return found


def _plan(string: Node, src: bytes) -> _Edit | None:
    start = next(c for c in string.children if c.type == "string_start")
    end = next(c for c in string.children if c.type == "string_end")
    content = src[start.end_byte : end.start_byte].decode("utf-8")
    content_lines = content.split("\n")
    if any(_ID_MARKER.match(line) for line in content_lines):
        return None
    marker_offsets = [i for i, line in enumerate(content_lines) if _LINKING_MARKER.match(line)]
    if not marker_offsets:
        return None
    offset = marker_offsets[-1]
    line = start.end_point.row + offset
    marker_text = content_lines[offset]
    if offset == 0:
        indent = _leading_whitespace(src, start)
        comment = ""
    else:
        indent = marker_text[: len(marker_text) - len(marker_text.lstrip(" \t"))]
        comment = _comment_prefix(marker_text.lstrip(" \t"))
    closing_on_line = end.start_point.row == line
    return _Edit(line, closing_on_line, end.start_point.column, indent + comment)


def _leading_whitespace(src: bytes, node: Node) -> str:
    line_start = src.rfind(b"\n", 0, node.start_byte) + 1
    prefix = src[line_start : node.start_byte].decode("utf-8")
    return prefix[: len(prefix) - len(prefix.lstrip(" \t"))]


def _comment_prefix(text: str) -> str:
    for prefix in ("///", "*", "#"):
        if text.startswith(prefix):
            rest = text[len(prefix) :]
            return prefix + rest[: len(rest) - len(rest.lstrip(" \t"))]
    return ""
