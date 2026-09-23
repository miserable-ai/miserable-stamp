"""Stamping `@id` markers into Python docstrings."""

import ast
import random
import re
from textwrap import dedent

from miserable_stamp.python import stamp_python

ID_LINE = re.compile(r"@id c-[0-9a-hjkmnp-tv-z]{10}")


def stamp(src: str, seed: int = 1) -> str:
    return stamp_python(dedent(src), random.Random(seed))


def test_id_goes_after_the_last_marker_with_its_indentation() -> None:
    after = stamp('''\
    def check_battery(level: int) -> None:
        """Raise the alert.

        @relation(SR-20, role=Implements)
        @model(agg-sensor-node, role=Implements)
        """
        if level < 20:
            raise_alert()
    ''')
    lines = after.splitlines()
    assert lines[4] == "    @model(agg-sensor-node, role=Implements)"
    assert ID_LINE.fullmatch(lines[5].strip())
    assert lines[5].startswith("    @id ")
    assert lines[6] == '    """'
    ast.parse(after)


def test_closing_quotes_on_the_marker_line_move_after_the_id() -> None:
    after = stamp('''\
    def check_battery(level: int) -> None:
        """@relation(SR-20, role=Implements)"""
        return None
    ''')
    lines = after.splitlines()
    assert lines[1] == '    """@relation(SR-20, role=Implements)'
    assert ID_LINE.fullmatch(lines[2].strip().removesuffix('"""'))
    assert lines[2].endswith('"""')
    assert lines[2].startswith("    @id ")
    assert lines[3] == "    return None"
    ast.parse(after)


def test_vector_a_style_with_markers_on_both_quote_lines() -> None:
    src = '''\
    class BatteryLevel:
        """@model(vo-battery-level, role=Implements)
        @relation(SR-1, role=Implements)"""
        percent: int = 100
    '''
    after = stamp(src)
    lines = after.splitlines()
    assert lines[2] == "    @relation(SR-1, role=Implements)"
    assert lines[3].startswith("    @id c-")
    assert lines[3].endswith('"""')
    ast.parse(after)


def test_symbols_with_an_id_or_without_markers_are_untouched() -> None:
    src = dedent('''\
    def a():
        """@relation(SR-1, role=Implements)
        @id c-7f3a9k2m1q"""


    def b():
        """Just documentation."""


    def c():
        pass
    ''')
    assert stamp_python(src, random.Random(1)) == src


def test_methods_and_nested_symbols_are_stamped_and_idempotent() -> None:
    src = '''\
    class Battery:
        """@model(agg-sensor-node, role=Implements)"""

        def is_low(self) -> bool:
            """@relation(SR-2, role=Implements)"""
            return True

        class Unit:
            """@model(vo-unit, role=Implements)"""
    '''
    once = stamp(src)
    assert len(ID_LINE.findall(once)) == 3
    assert stamp_python(once, random.Random(9)) == once
    tree = ast.parse(once)
    docstrings = [
        ast.get_docstring(n)
        for n in ast.walk(tree)
        if isinstance(n, ast.ClassDef | ast.FunctionDef)
    ]
    assert all(d is not None and "@id c-" in d for d in docstrings)


def test_ids_are_distinct_and_avoid_existing_ones() -> None:
    src = '''\
    def a():
        """@relation(SR-1, role=Implements)
        @id c-0000000000"""


    def b():
        """@relation(SR-2, role=Implements)"""


    def c():
        """@relation(SR-3, role=Implements)"""
    '''
    after = stamp(src)
    ids = ID_LINE.findall(after)
    assert len(ids) == len(set(ids)) == 3


def test_markers_outside_docstrings_are_not_stamped() -> None:
    src = dedent("""\
    # @relation(SR-1, role=Implements)
    def a():
        x = "@relation(SR-1, role=Implements)"
        return x
    """)
    assert stamp_python(src, random.Random(1)) == src


def test_files_that_do_not_parse_are_left_alone() -> None:
    src = 'def a(:\n    """@relation(SR-1, role=Implements)"""\n'
    assert stamp_python(src, random.Random(1)) == src


def test_seeded_stamping_is_deterministic() -> None:
    src = 'def a():\n    """@relation(SR-1, role=Implements)"""\n'
    assert stamp_python(src, random.Random(4)) == stamp_python(src, random.Random(4))
