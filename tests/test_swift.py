"""Stamping `@id` markers into Swift documentation comments."""

import random
import re
from textwrap import dedent

from miserable_stamp.code import _walk, error_free, language_for, stamp_code

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


def test_a_marked_protocol_requirement_is_stamped() -> None:
    after = stamp("""\
    protocol Probe {
        /// @relation(SR-3, role=Implements)
        func read() throws -> Int
    }
    """)
    lines = after.splitlines()
    assert re.fullmatch(r"    /// " + ID, lines[2])
    assert lines[3] == "    func read() throws -> Int"


# tree-sitter-swift 0.7.3 adds a visible MISSING `!` to valid Swift: after a property wrapper with
# empty arguments, and in `.success(())`. For Swift only ERROR nodes stop stamping, so such a file
# is stamped like any other.
VALID_WITH_MISSING = """\
struct Options {
    @Option() var name: String

    /// @relation(SR-4, role=Implements)
    func finish(completion: (Result<Void, Error>) -> Void) {
        completion(.success(()))
    }
}
"""


def test_a_visible_missing_node_does_not_stop_stamping_swift() -> None:
    assert SWIFT is not None
    nodes = list(_walk(SWIFT.parser.parse(VALID_WITH_MISSING.encode()).root_node))
    assert any(n.is_missing for n in nodes)
    assert not any(n.is_error for n in nodes)
    assert error_free(VALID_WITH_MISSING, SWIFT)
    after = stamp(VALID_WITH_MISSING)
    assert re.search(r"SR-4, role=Implements\)\n    /// " + ID + r"\n    func finish", after)
    assert error_free(after, SWIFT)
    assert stamp(after, seed=2) == after


def test_an_error_node_still_stops_stamping_swift() -> None:
    src = "/// @relation(SR-1, role=Implements)\nfunc a( {\n"
    assert SWIFT is not None
    assert not error_free(src, SWIFT)
    assert stamp(src) == src
