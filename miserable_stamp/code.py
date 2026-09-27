"""Stamping `@id` markers into the documentation comments of code symbols.

A symbol's documentation is the unbroken run of comments directly above its declaration: each
comment starts its own line, and only whitespace without a blank line separates it from the next
comment or from the declaration. A symbol whose documentation carries `@relation(...)` or
`@model(...)` but no `@id` gets `@id c-...` on a new line after the last marker, in the marker's
comment style: after a `///`, `//` or `#` line comes another such line; inside a `/** */` block
comes a line with the block's leading `*`. When the block closes on the marker's line, the closing
`*/` moves to the end of the new line. Files with syntax errors are left untouched.
"""

import random
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import tree_sitter_java
import tree_sitter_kotlin
import tree_sitter_swift
import tree_sitter_typescript
from tree_sitter import Language, Node, Parser

from miserable_stamp.ids import new_code_id

_COMMENT_START = r"[ \t]*(?:/\*\*|/\*|///|//|#|\*)?[ \t]*"
_LINKING_MARKER = re.compile(_COMMENT_START + r"@(?:relation|model)\(")
_ID_MARKER = re.compile(_COMMENT_START + r"@id\s+(c-[0-9a-hjkmnp-tv-z]{10})")
_LINE_COMMENT = re.compile(r"[ \t]*(?:///|//|#)")


@dataclass(frozen=True)
class CodeLanguage:
    """How to find documented symbols in one language."""

    name: str
    parser: Parser
    comments: frozenset[str]  # node types of comments
    is_symbol: Callable[[Node], bool]
    anchor: Callable[[Node], Node]  # the node the documentation sits above


@dataclass(frozen=True)
class _Edit:
    line: int  # 0-based line of the last marker
    close_column: int | None  # byte column of a block's closing `*/` on that line
    prefix: str  # indentation and comment syntax for the new line


def _types(*names: str) -> Callable[[Node], bool]:
    wanted = frozenset(names)
    return lambda node: node.type in wanted


def _itself(node: Node) -> Node:
    return node


KOTLIN = CodeLanguage(
    name="kotlin",
    parser=Parser(Language(tree_sitter_kotlin.language())),
    comments=frozenset({"line_comment", "block_comment"}),
    # `class_declaration` covers class, data class, enum class and interface.
    is_symbol=_types("function_declaration", "class_declaration", "object_declaration"),
    anchor=_itself,
)

JAVA = CodeLanguage(
    name="java",
    parser=Parser(Language(tree_sitter_java.language())),
    comments=frozenset({"line_comment", "block_comment"}),
    is_symbol=_types(
        "class_declaration",
        "interface_declaration",
        "enum_declaration",
        "record_declaration",
        "constructor_declaration",
        "method_declaration",
    ),
    anchor=_itself,
)

_TS_DECLARATIONS = frozenset(
    {"function_declaration", "class_declaration", "abstract_class_declaration", "method_definition"}
)
_TS_FUNCTION_VALUES = frozenset({"arrow_function", "function_expression"})
_TS_TEST_CALLS = frozenset({"it", "test"})


def _ts_symbol(node: Node) -> bool:
    if node.type in _TS_DECLARATIONS:
        return True
    if node.type == "lexical_declaration":
        # An exported `const name = () => ...`.
        exported = node.parent is not None and node.parent.type == "export_statement"
        return exported and any(
            (value := d.child_by_field_name("value")) is not None
            and value.type in _TS_FUNCTION_VALUES
            for d in node.named_children
            if d.type == "variable_declarator"
        )
    if node.type == "expression_statement":
        # A test call, `it("...", () => ...)` or `test("...", () => ...)`.
        call = node.named_children[0] if node.named_child_count else None
        function = call.child_by_field_name("function") if call is not None else None
        return (
            call is not None
            and call.type == "call_expression"
            and function is not None
            and function.type == "identifier"
            and function.text is not None
            and function.text.decode("utf-8") in _TS_TEST_CALLS
        )
    return False


def _ts_anchor(node: Node) -> Node:
    """JSDoc sits above `export`, and above a method's decorators, which the grammar puts beside
    the method rather than inside it."""
    if node.parent is not None and node.parent.type == "export_statement":
        return node.parent
    while node.prev_sibling is not None and node.prev_sibling.type == "decorator":
        node = node.prev_sibling
    return node


def _typescript(name: str, language: object) -> CodeLanguage:
    return CodeLanguage(
        name=name,
        parser=Parser(Language(language)),
        comments=frozenset({"comment"}),
        is_symbol=_ts_symbol,
        anchor=_ts_anchor,
    )


TYPESCRIPT = _typescript("typescript", tree_sitter_typescript.language_typescript())
TSX = _typescript("tsx", tree_sitter_typescript.language_tsx())


def _swift_symbol(node: Node) -> bool:
    if node.type in ("function_declaration", "protocol_declaration"):
        return True
    if node.type == "class_declaration":
        # class, struct, enum and extension share the node; an extension is no symbol itself,
        # only its members are.
        kind = node.child_by_field_name("declaration_kind")
        return kind is not None and kind.type != "extension"
    return False


SWIFT = CodeLanguage(
    name="swift",
    parser=Parser(Language(tree_sitter_swift.language())),
    comments=frozenset({"comment", "multiline_comment"}),
    is_symbol=_swift_symbol,
    anchor=_itself,
)

_SUFFIXES = {
    ".swift": SWIFT,
    ".ts": TYPESCRIPT,
    ".mts": TYPESCRIPT,
    ".cts": TYPESCRIPT,
    ".tsx": TSX,
    ".java": JAVA,
    ".kt": KOTLIN,
    ".kts": KOTLIN,
}


def language_for(path: str) -> CodeLanguage | None:
    """The code language of a file, by its name; None for files of other types."""
    name = path.rsplit("/", 1)[-1]
    for suffix, language in _SUFFIXES.items():
        if name.endswith(suffix):
            return language
    return None


def error_free(text: str, language: CodeLanguage) -> bool:
    """Whether `text` parses without ERROR nodes. MISSING nodes alone do not count: some grammars
    insert them into valid code."""
    root = language.parser.parse(text.encode("utf-8")).root_node
    return not root.has_error or not any(n.is_error for n in _walk(root))


def stamp_code(text: str, language: CodeLanguage, rng: random.Random) -> str:
    src = text.encode("utf-8")
    root = language.parser.parse(src).root_node
    if root.has_error and any(n.is_error for n in _walk(root)):
        return text
    comments = sorted(
        (n for n in _walk(root) if n.type in language.comments), key=lambda n: n.start_byte
    )
    anchors = {language.anchor(n).start_byte for n in _walk(root) if language.is_symbol(n)}
    edits = {
        e.line: e
        for start in anchors
        if (e := _plan(_documentation(comments, start, src), src)) is not None
    }
    taken = {m.group(1) for m in _ID_MARKER.finditer(text)}
    lines = _lines(text)
    for edit in sorted(edits.values(), key=lambda e: e.line, reverse=True):
        new_id = new_code_id(rng, taken)
        line = lines[edit.line]
        newline = "\r\n" if line.endswith("\r\n") else "\n"
        if edit.close_column is None:
            if not line.endswith("\n"):
                lines[edit.line] = line + newline
            lines.insert(edit.line + 1, f"{edit.prefix}@id {new_id}{newline}")
        else:
            raw = line.encode("utf-8")
            before = raw[: edit.close_column].decode("utf-8").rstrip()
            after = raw[edit.close_column :].decode("utf-8")
            lines[edit.line] = before + newline
            lines.insert(edit.line + 1, f"{edit.prefix}@id {new_id} {after}")
    return "".join(lines)


def _walk(root: Node) -> Iterator[Node]:
    cursor = root.walk()
    while True:
        node = cursor.node
        assert node is not None
        yield node
        if cursor.goto_first_child() or cursor.goto_next_sibling():
            continue
        while True:
            if not cursor.goto_parent():
                return
            if cursor.goto_next_sibling():
                break


def _documentation(comments: list[Node], start: int, src: bytes) -> list[Node]:
    """The run of comments directly above the byte offset `start`, top first."""
    run: list[Node] = []
    index = _last_before(comments, start)
    while index >= 0:
        comment = comments[index]
        gap = src[comment.end_byte : start]
        if gap.strip() or gap.count(b"\n") > 1 or not _starts_line(comment, src):
            break
        run.insert(0, comment)
        start = comment.start_byte
        index -= 1
    return run


def _last_before(comments: list[Node], start: int) -> int:
    index = len(comments) - 1
    while index >= 0 and comments[index].end_byte > start:
        index -= 1
    return index


def _starts_line(node: Node, src: bytes) -> bool:
    line_start = src.rfind(b"\n", 0, node.start_byte) + 1
    return not src[line_start : node.start_byte].strip()


def _plan(run: list[Node], src: bytes) -> _Edit | None:
    last: tuple[Node, int, str] | None = None
    for comment in run:
        for offset, raw in enumerate(src[comment.start_byte : comment.end_byte].split(b"\n")):
            line = raw.decode("utf-8").rstrip("\r")
            if _ID_MARKER.match(line):
                return None
            if _LINKING_MARKER.match(line):
                last = (comment, offset, line)
    if last is None:
        return None
    comment, offset, text = last
    row = comment.start_point.row + offset
    indent = _indent(src, comment)
    if _LINE_COMMENT.match(text):
        prefix = indent + text[: text.index("@")].lstrip(" \t")
        return _Edit(row, None, prefix)
    prefix = indent + " * " if offset == 0 else text[: text.index("@")]
    closes_here = comment.end_point.row == row
    return _Edit(row, comment.end_point.column - 2 if closes_here else None, prefix)


def _indent(src: bytes, node: Node) -> str:
    line_start = src.rfind(b"\n", 0, node.start_byte) + 1
    return src[line_start : node.start_byte].decode("utf-8")


def _lines(text: str) -> list[str]:
    """`text` split after each `\\n` only, as tree-sitter counts rows."""
    return re.findall(r"[^\n]*\n|[^\n]+$", text)
