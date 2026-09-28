"""Stamping `@id` markers into the documentation comments of code symbols.

A symbol's documentation is the unbroken run of comments directly above its declaration: each
comment starts its own line, and only whitespace without a blank line separates it from the next
comment or from the declaration. A symbol whose documentation carries `@relation(...)` or
`@model(...)` but no `@id` gets `@id c-...` on a new line after the last marker, in the marker's
comment style: after a `///`, `//` or `#` line comes another such line; inside a `/** */` block
comes a line with the block's leading `*`. When the block closes on the marker's line, the closing
`*/` moves to the end of the new line. Files with syntax errors are left untouched: a node reachable
through the parse tree's children is an ERROR node, or a MISSING node in every language but Swift,
whose grammar adds visible MISSING nodes to valid code.
"""

import random
import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import tree_sitter_hcl
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
    # Whether a MISSING node alone means the file does not parse; False for a grammar that adds
    # visible MISSING nodes to valid code.
    missing_is_error: bool = True
    # Whether a symbol is documented only by a `/** */` block, not by a run of line comments.
    needs_block: Callable[[Node], bool] = lambda node: False


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
    {
        "function_declaration",
        "function_signature",
        "class_declaration",
        "abstract_class_declaration",
    }
)
# Methods, and the overload signatures of a class; not the members of an interface.
_TS_MEMBERS = frozenset({"method_definition", "method_signature", "abstract_method_signature"})
_TS_FUNCTION_VALUES = frozenset({"arrow_function", "function_expression"})
# `it` and `test`, their `.only` and `.skip` forms, and each of those with `.each` (a table as
# arguments, `()`, or as a tagged template).
_TS_TEST_CALLS = frozenset(
    f"{base}{modifier}{each}"
    for base in ("it", "test")
    for modifier in ("", ".only", ".skip")
    for each in ("", ".each()")
)


def _ts_symbol(node: Node) -> bool:
    if node.type in _TS_DECLARATIONS:
        return True
    if node.type in _TS_MEMBERS:
        return node.parent is not None and node.parent.type == "class_body"
    if node.type == "lexical_declaration":
        # An exported `const name = () => ...`.
        exported = node.parent is not None and node.parent.type == "export_statement"
        return exported and any(
            (value := d.child_by_field_name("value")) is not None
            and value.type in _TS_FUNCTION_VALUES
            for d in node.named_children
            if d.type == "variable_declarator"
        )
    return _ts_test_call(node)


def _ts_test_call(node: Node) -> bool:
    """A test call statement, `it("...", () => ...)`, `test.skip(...)`, `test.each(table)(...)`,
    with a function after its title."""
    if node.type != "expression_statement" or not node.named_child_count:
        return False
    call = node.named_children[0]
    if call.type != "call_expression" or _call_path(call.child_by_field_name("function")) not in (
        _TS_TEST_CALLS
    ):
        return False
    arguments = call.child_by_field_name("arguments")
    values = [] if arguments is None else arguments.named_children[1:]
    return any(v.type in _TS_FUNCTION_VALUES for v in values)


def _call_path(node: Node | None) -> str | None:
    """A callee as a dotted path, a call in it written `()`: `it`, `test.skip`, `test.each()`."""
    if node is None:
        return None
    if node.type == "identifier":
        return node.text.decode("utf-8") if node.text is not None else None
    if node.type == "member_expression":
        base = _call_path(node.child_by_field_name("object"))
        member = node.child_by_field_name("property")
        if base is None or member is None or member.text is None:
            return None
        return f"{base}.{member.text.decode('utf-8')}"
    if node.type == "call_expression":
        inner = _call_path(node.child_by_field_name("function"))
        return None if inner is None else f"{inner}()"
    return None


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
        needs_block=_ts_test_call,  # a test call is documented only by a JSDoc block
    )


TYPESCRIPT = _typescript("typescript", tree_sitter_typescript.language_typescript())
TSX = _typescript("tsx", tree_sitter_typescript.language_tsx())


def _swift_symbol(node: Node) -> bool:
    if node.type in ("function_declaration", "protocol_declaration"):
        return True
    if node.type == "protocol_function_declaration":
        return True  # a protocol's function requirement
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
    # tree-sitter-swift 0.7.3 inserts a visible MISSING `!` into valid code: after a property
    # wrapper with empty arguments (`@Option() var x`) and in `.success(())`.
    missing_is_error=False,
)


def _hcl_blocks(*kinds: str) -> Callable[[Node], bool]:
    """Top-level blocks whose type is one of `kinds`."""
    wanted = frozenset(kinds)

    def is_symbol(node: Node) -> bool:
        body = node.parent
        return (
            node.type == "block"
            and body is not None
            and body.parent is not None
            and body.parent.type == "config_file"
            and node.named_child_count > 0
            and node.named_children[0].type == "identifier"
            and node.named_children[0].text is not None
            and node.named_children[0].text.decode("utf-8") in wanted
        )

    return is_symbol


def _hcl(name: str, *kinds: str) -> CodeLanguage:
    return CodeLanguage(
        name=name,
        parser=Parser(Language(tree_sitter_hcl.language())),
        comments=frozenset({"comment"}),
        is_symbol=_hcl_blocks(*kinds),
        anchor=_itself,
    )


HCL = _hcl("hcl", "resource", "module", "data")
TERRAFORM_TEST = _hcl("terraform test", "run")

_SUFFIXES = {
    ".tftest.hcl": TERRAFORM_TEST,
    ".tf": HCL,
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
    """Whether `text` parses: no node reachable through the tree's children is an ERROR node or,
    unless the language says otherwise (Swift), a MISSING node. A hidden MISSING node, which
    tree-sitter-kotlin reports for some valid one-liners, is not reachable and does not count."""
    return _parses(language.parser.parse(text.encode("utf-8")).root_node, language)


def _parses(root: Node, language: CodeLanguage) -> bool:
    missing = language.missing_is_error
    return not any(n.is_error or (missing and n.is_missing) for n in _walk(root))


def stamp_code(text: str, language: CodeLanguage, rng: random.Random) -> str:
    src = text.encode("utf-8")
    root = language.parser.parse(src).root_node
    if not _parses(root, language):
        return text
    comments = sorted(
        (n for n in _walk(root) if n.type in language.comments), key=lambda n: n.start_byte
    )
    anchors: dict[int, bool] = {}
    for node in _walk(root):
        if language.is_symbol(node):
            start = language.anchor(node).start_byte
            anchors[start] = anchors.get(start, False) or language.needs_block(node)
    edits = {
        e.line: e
        for start, needs_block in anchors.items()
        if (run := _documentation(comments, start, src))
        and (not needs_block or any(_is_block(c, src) for c in run))
        and (e := _plan(run, src)) is not None
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


def _is_block(comment: Node, src: bytes) -> bool:
    return src[comment.start_byte : comment.end_byte].startswith(b"/**")


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
