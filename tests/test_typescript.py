"""Stamping `@id` markers into TypeScript JSDoc blocks."""

import random
import re
from textwrap import dedent

from miserable_stamp.code import language_for, stamp_code

ID = r"@id c-[0-9a-hjkmnp-tv-z]{10}"


def stamp(src: str, path: str = "battery.ts", seed: int = 1) -> str:
    language = language_for(path)
    assert language is not None
    return stamp_code(dedent(src), language, random.Random(seed))


def test_typescript_suffixes_are_recognised() -> None:
    for path in ("a.ts", "a.tsx", "a.mts", "a.cts"):
        assert language_for(path) is not None
    assert language_for("a.js") is None
    assert language_for("a.jsx") is None


def test_jsdoc_above_export_is_the_documentation() -> None:
    after = stamp("""\
    /**
     * Raise the alert.
     * @relation(SR-20, role=Implements)
     */
    export function checkBattery(level: number): void {}
    """)
    lines = after.splitlines()
    assert lines[2] == " * @relation(SR-20, role=Implements)"
    assert re.fullmatch(r" \* " + ID, lines[3])
    assert lines[4] == " */"


def test_classes_methods_and_exported_const_arrows_are_stamped() -> None:
    after = stamp("""\
    /** @model(agg-sensor-node, role=Implements) */
    @Injectable()
    export class SensorNode {
      /** @relation(SR-1, role=Implements) */
      @Memo()
      isLow(): boolean {
        return true;
      }
    }

    /** @relation(SR-2, role=Implements) */
    export const charge = (percent: number): number => percent;

    /** @relation(SR-3, role=Implements) */
    const local = (): number => 1;

    /** @model(agg-base, role=Implements) */
    export abstract class Base {}
    """)
    assert len(re.findall(ID, after)) == 4
    lines = after.splitlines()
    assert lines[4] == "  /** @relation(SR-1, role=Implements)"
    assert re.fullmatch(r"   \* " + ID + r" \*/", lines[5])
    assert lines[6] == "  @Memo()"
    assert "const local" in after
    assert re.search(r"SR-3, role=Implements\) \*/\nconst local", after)


def test_test_calls_with_jsdoc_are_stamped() -> None:
    after = stamp(
        """\
        describe("battery", () => {
          /** @relation(AC-1, role=Verifies) */
          it("raises the alert below 20", () => {});

          /** @relation(AC-2, role=Verifies) */
          test("stays quiet above 20", () => {});

          /** @relation(AC-3, role=Verifies) */
          expect(1).toBe(1);
        });
        """,
        path="battery.test.ts",
    )
    assert len(re.findall(ID, after)) == 2


def test_tsx_components_are_stamped() -> None:
    after = stamp(
        """\
        /** @relation(SR-4, role=Implements) */
        export const Gauge = () => <div>{/* level */}</div>;
        """,
        path="gauge.tsx",
    )
    assert len(re.findall(ID, after)) == 1
