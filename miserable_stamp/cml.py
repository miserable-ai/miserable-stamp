"""Stamping `// id:` comments into Context Mapper (CML) models.

Every declaration of a Domain, Subdomain, BoundedContext, Aggregate, Entity, ValueObject,
DomainEvent, CommandEvent, Service, enum, UseCase or UserStory needs `// id: <id>` in the unbroken
run of `//` lines directly above it. Missing ids are inserted directly above the declaration, as
`<prefix>-<kebab-case name>`, with `-2`, `-3`, ... appended when that id is already taken. Existing
ids are never changed.
"""

import re

PREFIXES = {
    "Domain": "dom",
    "Subdomain": "sub",
    "BoundedContext": "ctx",
    "Aggregate": "agg",
    "Entity": "ent",
    "ValueObject": "vo",
    "DomainEvent": "ev",
    "CommandEvent": "cmd",
    "Service": "svc",
    "enum": "enum",
    "UseCase": "uc",
    "UserStory": "us",
}

_DECLARATION = re.compile(r"([ \t]*)(" + "|".join(PREFIXES) + r")[ \t]+([A-Za-z_][A-Za-z0-9_]*)\b")
_ID_LINE = re.compile(r"[ \t]*//\s*id:\s*(\S+)\s*")
_LINE_COMMENT = re.compile(r"[ \t]*//.*")
_BLOCK_COMMENT_LINE = re.compile(r"[ \t]*/\*.*\*/\s*")


def kebab_case(name: str) -> str:
    """`SensorNode` -> `sensor-node`, `HTTPClient` -> `http-client`, `a_b` -> `a-b`."""
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", name)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", text)
    text = re.sub(r"[-_]+", "-", text.replace("_", "-"))
    return text.strip("-").lower()


def existing_ids(text: str) -> set[str]:
    """Every id written on an `// id:` line in `text`."""
    return {m.group(1) for line in text.splitlines() if (m := _ID_LINE.fullmatch(line))}


def stamp_cml(text: str, taken: set[str]) -> str:
    """`text` with missing ids added. `taken` holds ids in use anywhere in the repository; the new
    ids are added to it."""
    lines = text.splitlines(keepends=True)
    bare = [line.rstrip("\r\n") for line in lines]
    newline = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
    inserts: list[tuple[int, str]] = []
    in_block = False
    for index, line in enumerate(bare):
        if in_block:
            in_block = "*/" not in line
            continue
        if "/*" in line and "*/" not in line.split("/*", 1)[1]:
            in_block = True
            continue
        match = _DECLARATION.match(line)
        if match is None or _has_id_above(bare, index):
            continue
        indent, keyword, name = match.groups()
        inserts.append((index, f"{indent}// id: {_new_id(PREFIXES[keyword], name, taken)}"))
    for index, id_line in reversed(inserts):
        lines.insert(index, id_line + newline)
    return "".join(lines)


def _has_id_above(lines: list[str], index: int) -> bool:
    for above in reversed(lines[:index]):
        if _ID_LINE.fullmatch(above):
            return True
        if not (_LINE_COMMENT.fullmatch(above) or _BLOCK_COMMENT_LINE.fullmatch(above)):
            return False
    return False


def _new_id(prefix: str, name: str, taken: set[str]) -> str:
    base = f"{prefix}-{kebab_case(name)}"
    candidate, suffix = base, 2
    while candidate in taken:
        candidate, suffix = f"{base}-{suffix}", suffix + 1
    taken.add(candidate)
    return candidate
