"""Stamping MIDs into StrictDoc documents."""

import difflib
import random
import re

from miserable_stamp.sdoc import stamp_sdoc

DOC = """\
[DOCUMENT]
MID: 7a0f4d4c1b5e4a8e9d8f2c3b7a1e0d99
TITLE: SRS alerts
OPTIONS:
  ENABLE_MID: True

[GRAMMAR]
IMPORT_FROM_FILE: @miserable

[TEXT]
STATEMENT: Introduction.

[[SECTION]]
TITLE: Battery

[REQUIREMENT]
UID: SR-88
KIND: functional
TITLE: Low battery alert
STATEMENT: >>>
The system shall raise an alert.
[REQUIREMENT]
This line only looks like an element tag.
<<<

[ACCEPTANCE_CRITERION]
MID: 33333333333333333333333333333333
UID: AC-201
STATEMENT: Given 19 %, an alert is shown.
METHOD: test

[[/SECTION]]

[USER_REQUIREMENT]
UID: UR-40
TITLE: Warn early
STATEMENT: The clinician is warned.

[ADR]
UID: ADR-0001
TITLE: Buffer readings
STATUS: accepted
CONTEXT: c
DECISION: d
CONSEQUENCES: e
"""

MID_LINE = re.compile(r"^MID: [0-9a-f]{32}\n$")


def inserted_lines(before: str, after: str) -> list[tuple[int, str]]:
    """(line index in `after`, text) for every inserted line; fails if anything else changed."""
    inserted = []
    matcher = difflib.SequenceMatcher(a=before.splitlines(True), b=after.splitlines(True))
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        assert tag in ("equal", "insert"), f"stamping changed existing lines: {tag}"
        if tag == "insert":
            inserted += [(j, after.splitlines(True)[j]) for j in range(j1, j2)]
    return inserted


def test_elements_without_a_mid_get_one_after_their_tag() -> None:
    after = stamp_sdoc(DOC, random.Random(1))
    lines = after.splitlines(True)
    added = inserted_lines(DOC, after)
    assert [lines[i - 1] for i, _ in added] == [
        "[REQUIREMENT]\n",
        "[USER_REQUIREMENT]\n",
        "[ADR]\n",
    ]
    assert all(MID_LINE.match(text) for _, text in added)


def test_text_document_and_look_alike_lines_are_left_alone() -> None:
    after = stamp_sdoc(DOC, random.Random(1))
    assert "[TEXT]\nSTATEMENT: Introduction." in after
    assert "[REQUIREMENT]\nThis line only looks like an element tag." in after


def test_stamping_is_idempotent() -> None:
    once = stamp_sdoc(DOC, random.Random(1))
    assert stamp_sdoc(once, random.Random(2)) == once


def test_seeded_stamping_is_deterministic_and_mids_are_distinct() -> None:
    first = stamp_sdoc(DOC, random.Random(7))
    assert first == stamp_sdoc(DOC, random.Random(7))
    mids = re.findall(r"^MID: ([0-9a-f]{32})$", first, re.MULTILINE)
    assert len(mids) == len(set(mids)) == 5


def test_mids_are_uuid4_hex() -> None:
    after = stamp_sdoc("[REQUIREMENT]\nUID: SR-1\n", random.Random(3))
    mid = after.splitlines()[1].removeprefix("MID: ")
    assert mid[12] == "4"
    assert mid[16] in "89ab"


def test_an_existing_mid_in_any_case_is_kept() -> None:
    doc = "[REQUIREMENT]\nMID: 2222222222222222222222222222222A\nUID: SR-1\n"
    assert stamp_sdoc(doc, random.Random(1)) == doc


def test_crlf_line_endings_are_preserved() -> None:
    after = stamp_sdoc("[REQUIREMENT]\r\nUID: SR-1\r\n", random.Random(1))
    assert after.split("\r\n")[1].startswith("MID: ")
    assert "\n" not in after.replace("\r\n", "")
