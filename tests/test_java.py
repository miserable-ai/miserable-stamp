"""Stamping `@id` markers into Javadoc blocks."""

import random
import re
from textwrap import dedent

from miserable_stamp.code import language_for, stamp_code

ID = r"@id c-[0-9a-hjkmnp-tv-z]{10}"
JAVA = language_for("Battery.java")


def stamp(src: str, seed: int = 1) -> str:
    assert JAVA is not None
    return stamp_code(dedent(src), JAVA, random.Random(seed))


def test_id_goes_after_the_last_marker_above_the_annotations() -> None:
    after = stamp("""\
    package ai.example;

    public class Battery {
        /**
         * Raise the alert.
         *
         * @relation(SR-20, role=Implements)
         */
        @Deprecated
        public void checkBattery(int level) {}
    }
    """)
    lines = after.splitlines()
    assert lines[6] == "     * @relation(SR-20, role=Implements)"
    assert re.fullmatch(r"     \* " + ID, lines[7])
    assert lines[8] == "     */"
    assert lines[9] == "    @Deprecated"


def test_classes_interfaces_enums_records_and_constructors_are_stamped() -> None:
    after = stamp("""\
    /** @model(agg-sensor-node, role=Implements) */
    public class SensorNode {
        /** @relation(SR-1, role=Implements) */
        public SensorNode() {}

        /** @model(vo-battery-level, role=Implements) */
        public record BatteryLevel(int percent) {}

        /** @model(enum-unit, role=Implements) */
        public enum Unit { PERCENT }

        /** @model(svc-alerts, role=Implements) */
        public interface Alerts {
            /** @relation(SR-2, role=Implements) */
            void raise();
        }
    }
    """)
    assert len(re.findall(ID, after)) == 6
    lines = after.splitlines()
    assert lines[0] == "/** @model(agg-sensor-node, role=Implements)"
    assert re.fullmatch(r" \* " + ID + r" \*/", lines[1])


def test_a_plain_comment_between_javadoc_and_declaration_joins_the_run() -> None:
    after = stamp("""\
    class A {
        /** @relation(SR-1, role=Implements) */
        // TODO tidy up
        void a() {}
    }
    """)
    assert len(re.findall(ID, after)) == 1


def test_markers_in_a_body_or_after_a_blank_line_are_not_stamped() -> None:
    src = dedent("""\
    class A {
        /** @relation(SR-1, role=Implements) */

        void a() {
            /** @relation(SR-2, role=Implements) */
            int x = 1;
        }
    }
    """)
    assert stamp(src) == src
