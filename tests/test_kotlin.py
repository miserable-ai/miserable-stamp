"""Stamping `@id` markers into Kotlin KDoc blocks."""

import random
import re
from textwrap import dedent

from miserable_stamp.code import language_for, stamp_code

ID = r"@id c-[0-9a-hjkmnp-tv-z]{10}"
KOTLIN = language_for("Battery.kt")


def stamp(src: str, seed: int = 1) -> str:
    assert KOTLIN is not None
    return stamp_code(dedent(src), KOTLIN, random.Random(seed))


def test_kotlin_suffixes_are_recognised() -> None:
    assert language_for("a/Battery.kt") is KOTLIN
    assert language_for("build.gradle.kts") is KOTLIN


def test_id_goes_after_the_last_marker_of_the_kdoc_block() -> None:
    after = stamp("""\
    package ai.example

    /**
     * Raise the alert.
     *
     * @relation(SR-20, role=Implements)
     * @model(agg-sensor-node, role=Implements)
     */
    @Throws(IllegalStateException::class)
    fun checkBattery(level: Int) {
        if (level < 20) raiseAlert()
    }
    """)
    lines = after.splitlines()
    assert lines[6] == " * @model(agg-sensor-node, role=Implements)"
    assert re.fullmatch(r" \* " + ID, lines[7])
    assert lines[8] == " */"
    assert lines[9] == "@Throws(IllegalStateException::class)"


def test_a_one_line_kdoc_is_split_before_its_closing_delimiter() -> None:
    after = stamp("""\
    class Battery {
        /** @relation(SR-2, role=Implements) */
        fun isLow(): Boolean = true
    }
    """)
    lines = after.splitlines()
    assert lines[1] == "    /** @relation(SR-2, role=Implements)"
    assert re.fullmatch(r"     \* " + ID + r" \*/", lines[2])
    assert lines[3] == "    fun isLow(): Boolean = true"


def test_classes_objects_interfaces_and_companion_members_are_stamped() -> None:
    after = stamp("""\
    /** @model(vo-battery-level, role=Implements) */
    data class BatteryLevel(val percent: Int)

    /** @model(enum-unit, role=Implements) */
    enum class Unit { PERCENT }

    /** @model(svc-charging, role=Implements) */
    object Charging

    /** @model(svc-alerts, role=Implements) */
    interface Alerts {
        fun raise()
    }

    class Battery {
        companion object {
            /** @relation(SR-3, role=Implements) */
            fun make(): Battery = Battery()
        }
    }
    """)
    assert len(re.findall(ID, after)) == 5


def test_markers_in_a_run_of_line_comments_get_a_line_comment_id() -> None:
    after = stamp("""\
    // Raise the alert.
    // @relation(SR-20, role=Implements)
    fun checkBattery(level: Int) {}
    """)
    lines = after.splitlines()
    assert lines[1] == "// @relation(SR-20, role=Implements)"
    assert re.fullmatch(r"// " + ID, lines[2])
    assert lines[3] == "fun checkBattery(level: Int) {}"


def test_a_blank_line_ends_the_documentation() -> None:
    src = dedent("""\
    /** @relation(SR-20, role=Implements) */

    fun checkBattery(level: Int) {}
    """)
    assert stamp(src) == src


def test_symbols_with_an_id_or_without_markers_are_untouched() -> None:
    src = dedent("""\
    /**
     * @relation(SR-1, role=Implements)
     * @id c-7f3a9k2m1q
     */
    fun a() {}

    /** Just documentation. */
    fun b() {}

    fun c() {}
    """)
    assert stamp(src) == src


def test_markers_inside_a_body_are_not_stamped() -> None:
    src = dedent("""\
    fun a() {
        // @relation(SR-1, role=Implements)
        val x = 1
    }
    """)
    assert stamp(src) == src


def test_a_hidden_missing_node_does_not_stop_stamping() -> None:
    # tree-sitter-kotlin 1.1.0 reports a hidden MISSING node for this valid one-liner, which no
    # walk through the tree's children reaches.
    after = stamp("""\
    /** @model(svc-alerts, role=Implements) */
    interface Alerts { fun raise(): Int }
    """)
    assert len(re.findall(ID, after)) == 1
