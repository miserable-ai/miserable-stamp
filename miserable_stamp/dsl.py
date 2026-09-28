"""Stamping `miserable.id` properties into Structurizr DSL deployment elements.

Every `deploymentNode`, `infrastructureNode`, `containerInstance` and `softwareSystemInstance`
needs `"miserable.id" "dep-<name>"` in its own `properties` block. A missing id is added as the
first line of that block; the block is created as the first thing inside the element when there is
none, and the element's braces are opened when it has none. The name is the element's name, and for
an instance the name of the container or software system it instantiates (its identifier when the
repository's DSL does not define it), in kebab case, with `-2`, `-3`, ... appended when that id is
already taken. Existing ids are never changed.

The DSL is line-oriented: `{` ends the line that opens a block and `}` stands on a line of its own,
so the stamper reads it line by line and needs no parser.
"""

import re
from dataclasses import dataclass

from miserable_stamp.cml import kebab_case

_KINDS = "deploymentNode|infrastructureNode|containerInstance|softwareSystemInstance"
_ELEMENT = re.compile(
    r"(?P<indent>[ \t]*)(?:[\w.-]+[ \t]*=[ \t]*)?(?P<kind>" + _KINDS + r")\b(?P<rest>.*)",
    re.IGNORECASE,
)
_PROPERTIES = re.compile(r"[ \t]*properties[ \t]*\{[ \t]*", re.IGNORECASE)
_ID_PROPERTY = re.compile(r'[ \t]*"?miserable\.id"?[ \t]+"?([^"\s]+)"?[ \t]*')
_DEFINITION = re.compile(
    r'[ \t]*([\w-]+)[ \t]*=[ \t]*(?:container|softwareSystem)[ \t]+"([^"]*)"', re.IGNORECASE
)
_FIRST_ARGUMENT = re.compile(r'[ \t]*(?:"([^"]*)"|([^\s{"]+))')
_EMPTY_BRACES = re.compile(r"\{[ \t]*\}[ \t]*$")


@dataclass
class _Block:
    line: int  # 0-based line that opens the block
    kind: str  # "element", "properties" or "other"
    name: str = ""
    properties: int | None = None  # the line opening the element's own properties block
    has_id: bool = False


def kebab_name(name: str) -> str:
    """`Amazon Web Services` -> `amazon-web-services`, `DynamoDB` -> `dynamo-db`."""
    words = re.split(r"[^A-Za-z0-9]+", name)
    text = "-".join(kebab_case(word) for word in words if word)
    return re.sub(r"-+", "-", text).strip("-") or "element"


def existing_ids(text: str) -> set[str]:
    """Every `miserable.id` value written in `text`."""
    return {m.group(1) for line in _bare(text) if (m := _ID_PROPERTY.fullmatch(line))}


def element_names(text: str) -> dict[str, str]:
    """The name of each container and software system that `text` defines with an identifier."""
    return {m.group(1): m.group(2) for line in _bare(text) if (m := _DEFINITION.match(line))}


def stamp_dsl(text: str, taken: set[str], names: dict[str, str]) -> str:
    """`text` with missing ids added. `taken` holds ids in use anywhere in the repository's DSL; the
    new ids are added to it. `names` maps identifiers to the names of the elements they define."""
    lines = _lines(text)
    bare = [line.rstrip("\r\n") for line in lines]
    newline = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
    unit = _indent_unit(bare)
    todo: list[_Block] = []  # elements without an id, in document order
    stack: list[_Block] = []
    in_comment = False
    for index, line in enumerate(bare):
        stripped = line.strip()
        if in_comment:
            in_comment = "*/" not in stripped
            continue
        if stripped.startswith("/*"):
            in_comment = "*/" not in stripped[2:]
            continue
        if not stripped or stripped.startswith(("#", "//")):
            continue
        if stripped == "}":
            if stack:
                block = stack.pop()
                if block.kind == "element" and not block.has_id:
                    todo.append(block)
            continue
        top = stack[-1] if stack else None
        if top is not None and top.kind == "properties" and _ID_PROPERTY.fullmatch(line):
            parent = stack[-2] if len(stack) > 1 else None
            if parent is not None and parent.kind == "element":
                parent.has_id = True
            continue
        element = _ELEMENT.fullmatch(line)
        opens = stripped.endswith("{")
        if element is not None:
            block = _Block(index, "element", _name(element, names))
            if opens:
                stack.append(block)
            else:
                todo.append(block)
        elif opens:
            if top is not None and top.kind == "element" and _PROPERTIES.fullmatch(line):
                top.properties = index
                stack.append(_Block(index, "properties"))
            else:
                stack.append(_Block(index, "other"))
    ids = {block.line: _new_id(block.name, taken) for block in sorted(todo, key=lambda b: b.line)}
    for block in sorted(todo, key=lambda b: b.line, reverse=True):
        _insert(lines, bare, block, ids[block.line], unit, newline)
    return "".join(lines)


def _insert(
    lines: list[str], bare: list[str], block: _Block, new_id: str, unit: str, newline: str
) -> None:
    indent = _indent(bare[block.line])
    id_line = f'"miserable.id" "{new_id}"'
    if block.properties is not None:
        inner = _inner_indent(bare, block.properties, _indent(bare[block.properties]) + unit)
        lines.insert(block.properties + 1, inner + id_line + newline)
        return
    line = bare[block.line]
    if line.rstrip().endswith("{") and not _EMPTY_BRACES.search(line):
        properties_indent = _inner_indent(bare, block.line, indent + unit)
        closing: list[str] = []
    else:
        # No braces, or `{}` on the element's line: open them here and close them below.
        opened = _EMPTY_BRACES.sub("", line).rstrip() + " {"
        lines[block.line] = opened + newline
        properties_indent = indent + unit
        closing = [indent + "}" + newline]
    new = [
        properties_indent + "properties {" + newline,
        properties_indent + unit + id_line + newline,
        properties_indent + "}" + newline,
        *closing,
    ]
    if not lines[block.line].endswith("\n"):
        lines[block.line] += newline
    lines[block.line + 1 : block.line + 1] = new


def _name(element: re.Match[str], names: dict[str, str]) -> str:
    argument = _FIRST_ARGUMENT.match(element.group("rest"))
    if argument is None:
        return element.group("kind")
    if argument.group(1) is not None:
        return argument.group(1)
    word = argument.group(2)
    if element.group("kind").lower().endswith("instance"):
        return names.get(word.rsplit(".", 1)[-1], word)
    return word


def _new_id(name: str, taken: set[str]) -> str:
    base = f"dep-{kebab_name(name)}"
    candidate, suffix = base, 2
    while candidate in taken:
        candidate, suffix = f"{base}-{suffix}", suffix + 1
    taken.add(candidate)
    return candidate


def _inner_indent(bare: list[str], opening: int, default: str) -> str:
    """The indentation of the first line inside the block opened on line `opening`, or `default`
    when the block is empty or its first line is not indented deeper than its opening."""
    outer = _indent(bare[opening])
    for line in bare[opening + 1 :]:
        if line.strip():
            inner = _indent(line)
            return inner if line.strip() != "}" and len(inner) > len(outer) else default
    return default


def _indent_unit(bare: list[str]) -> str:
    for line in bare:
        if line.strip() and line[0] in " \t":
            return _indent(line)
    return "    "


def _indent(line: str) -> str:
    return line[: len(line) - len(line.lstrip(" \t"))]


def _bare(text: str) -> list[str]:
    return [line.rstrip("\r\n") for line in _lines(text)]


def _lines(text: str) -> list[str]:
    return re.findall(r"[^\n]*\n|[^\n]+$", text)
