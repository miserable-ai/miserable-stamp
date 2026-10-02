"""Properties every code language's stamping keeps."""

import difflib
import random
import re

import pytest

from miserable_stamp.code import _walk, error_free, language_for, stamp_code

ID = re.compile(r"@id (c-[0-9a-hjkmnp-tv-z]{10})")

# One sample per language: three marked symbols, one of them already stamped, plus an unmarked
# one. The markers never share a line with a closing `*/`, so stamping only adds lines.
SAMPLES = {
    "battery.c": """\
#include "battery.h"

/**
 * @relation(SR-1, role=Implements)
 * @id c-0000000000
 */
int a(void) { return 1; }

/**
 * Two markers.
 * @relation(SR-2, role=Implements)
 * @model(svc-b, role=Implements)
 */
static int b(int x) { return x; }

/**
 * @model(vo-battery, role=Implements)
 */
struct battery { int level; };

int d(void) { return 0; }
""",
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
    "Battery.java": """\
package ai.example;

/**
 * @model(agg-battery, role=Implements)
 * @id c-0000000000
 */
public class Battery {
    /**
     * Two markers.
     * @relation(SR-2, role=Implements)
     * @model(svc-b, role=Implements)
     */
    @Deprecated
    public void b() {}

    /**
     * @relation(SR-3, role=Implements)
     */
    public int c() { return 1; }

    void d() {}
}
""",
    "battery.ts": """\
/**
 * @model(agg-battery, role=Implements)
 * @id c-0000000000
 */
export class Battery {
  /**
   * Two markers.
   * @relation(SR-2, role=Implements)
   * @model(svc-b, role=Implements)
   */
  b(): void {}
}

/**
 * @relation(SR-3, role=Implements)
 */
export function c(): number {
  return 1;
}

function d(): void {}
""",
    "Battery.swift": """\
/// @model(agg-battery, role=Implements)
/// @id c-0000000000
final class Battery {
    /// Two markers.
    /// @relation(SR-2, role=Implements)
    /// @model(svc-b, role=Implements)
    func b() {}

    /**
     * @relation(SR-3, role=Implements)
     */
    func c() -> Int { 1 }

    func d() {}
}
""",
    "main.tf": """\
# @model(dep-bucket, role=Implements)
# @id c-0000000000
resource "aws_s3_bucket" "b" {
  bucket = "b"
}

# Two markers.
# @relation(SR-2, role=Implements)
// @model(dep-alerts, role=Implements)
module "alerts" {
  source = "./alerts"
}

/*
 * @relation(SR-3, role=Implements)
 */
data "aws_region" "current" {}

locals {
  d = 1
}
""",
}

BROKEN = {
    "Battery.kt": "/** @relation(SR-1, role=Implements) */\nfun a( {\n",
    "Battery.java": "/** @relation(SR-1, role=Implements) */\nclass A { void a() { int = ; } }\n",
    "battery.ts": "/** @relation(SR-1, role=Implements) */\nexport function a() { let = ; }\n",
    "Battery.swift": "/// @relation(SR-1, role=Implements)\nfunc a() { let = }\n",
    "main.tf": '# @relation(SR-1, role=Implements)\nresource "a" "b" {\n  = 1\n}\n',
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


# A visible MISSING node is a token the file lacks: such a file does not parse either. Swift is the
# exception (`test_swift.py`): its grammar adds visible MISSING nodes to valid code.
MISSING_ONLY = {
    "Battery.kt": "/** @relation(SR-1, role=Implements) */\nfun a() { f(1 }\n",
    "Battery.java": "/** @relation(SR-1, role=Implements) */\nclass A { void a() { int x = 1 } }\n",
    "battery.ts": "/** @relation(SR-1, role=Implements) */\nexport function a() { f(1; }\n",
    "main.tf": '# @relation(SR-1, role=Implements)\nresource "a" "b" {\n',
}


@pytest.mark.parametrize("path", MISSING_ONLY)
def test_files_with_only_a_missing_node_are_left_alone(path: str) -> None:
    language = language_for(path)
    assert language is not None
    nodes = list(_walk(language.parser.parse(MISSING_ONLY[path].encode()).root_node))
    assert not any(n.is_error for n in nodes)
    assert any(n.is_missing for n in nodes)
    assert not error_free(MISSING_ONLY[path], language)
    assert stamp(path, MISSING_ONLY[path]) == MISSING_ONLY[path]


def test_other_files_have_no_code_language() -> None:
    assert language_for("notes.md") is None
    assert language_for("main.hcl") is None
