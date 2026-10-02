"""Stamping `@id` markers into C documentation comments."""

import random
import re
from textwrap import dedent

from miserable_stamp.code import _walk, language_for, stamp_code

ID = r"@id c-[0-9a-hjkmnp-tv-z]{10}"
C = language_for("battery.c")


def stamp(src: str, seed: int = 1) -> str:
    assert C is not None
    return stamp_code(dedent(src), C, random.Random(seed))


def ids(text: str) -> list[str]:
    return re.findall(ID, text)


def test_c_and_header_files_are_c() -> None:
    assert C is not None
    assert C.name == "c"
    assert language_for("include/battery.h") is C


def test_a_function_definition_gets_a_star_line_in_its_block() -> None:
    after = stamp("""\
    /**
     * Raise the alert below 20%.
     * @relation(SR-20, role=Implements)
     */
    static int check_battery(int level)
    {
        return level < 20;
    }
    """)
    lines = after.splitlines()
    assert lines[2] == " * @relation(SR-20, role=Implements)"
    assert re.fullmatch(r" \* " + ID, lines[3])
    assert lines[4] == " */"


def test_a_line_comment_run_gets_another_line_comment() -> None:
    after = stamp("""\
    // @relation(SR-20, role=Implements)
    int check_battery(int level) { return level < 20; }
    """)
    assert re.fullmatch(r"// " + ID, after.splitlines()[1])


def test_structs_unions_enums_and_typedef_structs_are_stamped() -> None:
    after = stamp("""\
    /** @model(vo-battery, role=Implements) */
    struct battery { int level; };

    /** @model(vo-reading, role=Implements) */
    union reading { int raw; float volts; };

    /** @model(enum-mode, role=Implements) */
    enum mode { OFF, ON };

    /** @model(vo-anon, role=Implements) */
    typedef struct { int a; } anon_t;
    """)
    assert len(ids(after)) == 4


def test_prototypes_and_nested_structs_are_not_stamped() -> None:
    src = """\
    /** @relation(SR-20, role=Implements) */
    int check_battery(int level);

    struct outer {
        /** @model(vo-inner, role=Implements) */
        struct inner { int x; } in;
    };
    """
    assert stamp(src) == dedent(src)


def test_definitions_inside_conditionals_and_extern_c_are_stamped() -> None:
    after = stamp("""\
    #ifdef LOW_POWER
    /** @relation(SR-21, role=Implements) */
    int read_level(void) { return 1; }
    #else
    /** @relation(SR-21, role=Implements) */
    int read_level(void) { return 2; }
    #endif

    extern "C" {
    /** @relation(SR-22, role=Implements) */
    int in_extern(void) { return 0; }
    }
    """)
    assert len(set(ids(after))) == 3


def test_a_definition_with_an_error_node_is_left_unstamped_and_the_rest_are() -> None:
    src = dedent("""\
    /** @relation(SR-1, role=Implements) */
    int good(void) { return 1; }

    /** @relation(SR-2, role=Implements) */
    int bad(void) { int x = ) ; return x; }
    """)
    assert C is not None
    assert any(n.is_error for n in _walk(C.parser.parse(src.encode()).root_node))
    after = stamp(src)
    assert len(ids(after)) == 1
    assert after.index("@id") < after.index("int good")
    assert "int bad(void) { int x = ) ; return x; }" in after


def test_a_definition_with_a_missing_node_is_left_unstamped() -> None:
    src = dedent("""\
    /** @relation(SR-1, role=Implements) */
    int bad(void) { return f(1; }
    """)
    assert C is not None
    nodes = list(_walk(C.parser.parse(src.encode()).root_node))
    assert any(n.is_missing or n.is_error for n in nodes)
    assert stamp(src) == src


def test_an_error_outside_every_definition_does_not_stop_stamping() -> None:
    src = dedent("""\
    DEFINE_THING(a, b) = { .x = 1 };

    /** @relation(SR-1, role=Implements) */
    int good(void) { return 1; }
    """)
    assert C is not None
    assert any(n.is_error for n in _walk(C.parser.parse(src.encode()).root_node))
    assert len(ids(stamp(src))) == 1


def test_stamping_adds_no_error_or_missing_node() -> None:
    src = dedent("""\
    /** @relation(SR-1, role=Implements) */
    int good(void) { return 1; }

    /**
     * @relation(SR-2, role=Implements) */
    int also(void) { return 2; }
    """)
    assert C is not None
    after = stamp(src)

    def faults(text: str) -> int:
        tree = C.parser.parse(text.encode())
        return sum(n.is_error or n.is_missing for n in _walk(tree.root_node))

    assert len(ids(after)) == 2
    assert faults(after) == faults(src) == 0
