"""Stamping `@id` markers into Swift documentation comments."""

import random
import re
from textwrap import dedent

from miserable_stamp.code import language_for, stamp_code

ID = r"@id c-[0-9a-hjkmnp-tv-z]{10}"
SWIFT = language_for("Battery.swift")


def stamp(src: str, seed: int = 1) -> str:
    assert SWIFT is not None
    return stamp_code(dedent(src), SWIFT, random.Random(seed))


def test_id_goes_on_a_new_triple_slash_line_after_the_last_marker() -> None:
    after = stamp("""\
    /// Raise the alert.
    /// @relation(SR-20, role=Implements)
    /// @model(agg-sensor-node, role=Implements)
    @MainActor
    public func checkBattery(level: Int) -> Alert? { nil }
    """)
    lines = after.splitlines()
    assert lines[2] == "/// @model(agg-sensor-node, role=Implements)"
    assert re.fullmatch(r"/// " + ID, lines[3])
    assert lines[4] == "@MainActor"


def test_a_block_comment_gets_a_star_line() -> None:
    after = stamp("""\
    /**
     * @model(vo-battery-level, role=Implements)
     */
    struct BatteryLevel {
        let percent: Int
    }
    """)
    lines = after.splitlines()
    assert re.fullmatch(r" \* " + ID, lines[2])
    assert lines[3] == " */"


def test_types_protocols_and_extension_members_are_stamped() -> None:
    after = stamp("""\
    /// @model(agg-sensor-node, role=Implements)
    final class SensorNode {
        /// @relation(SR-1, role=Implements)
        func isLow() -> Bool { true }
    }

    /// @model(enum-unit, role=Implements)
    enum Unit { case percent }

    /// @model(svc-alerts, role=Implements)
    protocol Alerts {
        func raise()
    }

    /// @relation(SR-9, role=Implements)
    extension SensorNode {
        /// @relation(SR-2, role=Implements)
        func charge() {}
    }
    """)
    assert len(re.findall(ID, after)) == 5
    assert re.search(r"SR-9, role=Implements\)\nextension", after)


def test_markers_after_a_blank_line_are_not_stamped() -> None:
    src = dedent("""\
    /// @relation(SR-1, role=Implements)

    func a() {}
    """)
    assert stamp(src) == src
