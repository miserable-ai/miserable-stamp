"""Properties every code language's stamping keeps."""

import difflib
import random
import re

import pytest

from miserable_stamp.code import error_free, language_for, stamp_code

ID = re.compile(r"@id (c-[0-9a-hjkmnp-tv-z]{10})")

# One sample per language: three marked symbols, one of them already stamped, plus an unmarked
# one. The markers never share a line with a closing `*/`, so stamping only adds lines.
SAMPLES = {
    "Battery.kt": """\
package ai.example

/**
 * @relation(SR-1, role=Implements)
 * @id c-0000000000
 */
fun a() {}

/**
 * Two markers.
 * @relation(SR-2, role=Implements)
 * @model(svc-b, role=Implements)
 */
fun b() {}

class Battery {
    /**
     * @model(vo-battery, role=Implements)
     */
    fun c(): Int = 1

    fun d() {}
}
""",
}

BROKEN = {
    "Battery.kt": "/** @relation(SR-1, role=Implements) */\nfun a( {\n",
}


def stamp(path: str, text: str, seed: int = 1) -> str:
    language = language_for(path)
    assert language is not None
    return stamp_code(text, language, random.Random(seed))


def added(before: str, after: str) -> list[str]:
    """The lines `after` adds to `before`; fails if any line of `before` changed otherwise."""
    lines = []
    matcher = difflib.SequenceMatcher(a=before.splitlines(True), b=after.splitlines(True))
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        assert tag in ("equal", "insert"), "stamping changed existing lines"
        if tag == "insert":
            lines += after.splitlines(True)[j1:j2]
    return lines


@pytest.mark.parametrize("path", SAMPLES)
def test_only_id_lines_are_added(path: str) -> None:
    before = SAMPLES[path]
    new = added(before, stamp(path, before))
    assert len(new) == 2
    assert all(ID.search(line) for line in new)


@pytest.mark.parametrize("path", SAMPLES)
def test_ids_are_distinct_and_avoid_existing_ones(path: str) -> None:
    ids = ID.findall(stamp(path, SAMPLES[path]))
    assert len(ids) == len(set(ids)) == 3


@pytest.mark.parametrize("path", SAMPLES)
def test_stamping_is_idempotent(path: str) -> None:
    once = stamp(path, SAMPLES[path])
    assert stamp(path, once, seed=9) == once


@pytest.mark.parametrize("path", SAMPLES)
def test_seeded_stamping_is_deterministic(path: str) -> None:
    assert stamp(path, SAMPLES[path], seed=4) == stamp(path, SAMPLES[path], seed=4)


@pytest.mark.parametrize("path", SAMPLES)
def test_stamped_files_still_parse(path: str) -> None:
    language = language_for(path)
    assert language is not None
    assert error_free(SAMPLES[path], language)
    assert error_free(stamp(path, SAMPLES[path]), language)


@pytest.mark.parametrize("path", SAMPLES)
def test_crlf_is_preserved(path: str) -> None:
    before = SAMPLES[path].replace("\n", "\r\n")
    after = stamp(path, before)
    assert after != before
    assert "\n" not in after.replace("\r\n", "")


@pytest.mark.parametrize("path", BROKEN)
def test_files_that_do_not_parse_are_left_alone(path: str) -> None:
    assert stamp(path, BROKEN[path]) == BROKEN[path]


def test_other_files_have_no_code_language() -> None:
    assert language_for("notes.md") is None
    assert language_for("main.hcl") is None
