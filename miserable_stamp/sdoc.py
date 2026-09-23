"""Stamping MIDs into StrictDoc documents.

Every user requirement, requirement, acceptance criterion and ADR without a `MID:` field gets one
on the line directly after its element tag. No other line changes. Multi-line field values
(`>>>` ... `<<<`) are skipped, so a line inside them that looks like a tag is never taken for one.
"""

import random
import re

from miserable_stamp.ids import new_mid

_ELEMENT = re.compile(r"\[(USER_REQUIREMENT|REQUIREMENT|ACCEPTANCE_CRITERION|ADR)\]\s*")
_MID_FIELD = re.compile(r"MID:\s*(\S+)\s*")
_BLOCK_START = re.compile(r"[A-Z_]+:\s*>>>\s*")
_BLOCK_END = "<<<"


def stamp_sdoc(text: str, rng: random.Random) -> str:
    lines = text.splitlines(keepends=True)
    newline = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
    taken = {m.group(1).lower() for m in map(_MID_FIELD.fullmatch, _bare(lines)) if m}
    insert_after: list[int] = []
    element: int | None = None
    has_mid = False
    in_block = False
    for index, line in enumerate(_bare(lines)):
        if in_block:
            in_block = line.strip() != _BLOCK_END
            continue
        if line.startswith("["):
            if element is not None and not has_mid:
                insert_after.append(element)
            element = index if _ELEMENT.fullmatch(line) else None
            has_mid = False
        elif _MID_FIELD.fullmatch(line):
            has_mid = True
        elif _BLOCK_START.fullmatch(line):
            in_block = True
    if element is not None and not has_mid:
        insert_after.append(element)
    for index in reversed(insert_after):
        if not lines[index].endswith(("\n", "\r")):
            lines[index] += newline
        lines.insert(index + 1, f"MID: {new_mid(rng, taken)}{newline}")
    return "".join(lines)


def _bare(lines: list[str]) -> list[str]:
    return [line.rstrip("\r\n") for line in lines]
