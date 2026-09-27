"""The `miserable-stamp` command that pre-commit runs on staged files."""

from pathlib import Path

import pytest

from miserable_stamp.cli import main


def test_changed_files_are_listed_and_fail_the_hook(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = tmp_path / "battery.py"
    code.write_text('def a():\n    """@relation(SR-1, role=Implements)"""\n')
    spec = tmp_path / "srs.sdoc"
    spec.write_text("[REQUIREMENT]\nUID: SR-1\n")
    other = tmp_path / "notes.md"
    other.write_text("@relation(SR-1, role=Implements)\n")

    assert main([str(code), str(spec), str(other)]) == 1
    out = capsys.readouterr().out
    assert str(code) in out
    assert str(spec) in out
    assert str(other) not in out
    assert "@id c-" in code.read_text()
    assert "MID: " in spec.read_text()
    assert other.read_text() == "@relation(SR-1, role=Implements)\n"


def test_code_in_other_languages_is_stamped(tmp_path: Path) -> None:
    code = tmp_path / "Battery.kt"
    code.write_text("/** @relation(SR-1, role=Implements) */\nfun a() {}\n")
    assert main([str(code)]) == 1
    assert "@id c-" in code.read_text()


def test_nothing_to_stamp_passes(tmp_path: Path) -> None:
    code = tmp_path / "a.py"
    code.write_text("def a():\n    pass\n")
    assert main([str(code)]) == 0


def test_second_run_passes(tmp_path: Path) -> None:
    code = tmp_path / "a.py"
    code.write_text('def a():\n    """@relation(SR-1, role=Implements)"""\n')
    assert main([str(code)]) == 1
    assert main([str(code)]) == 0


def test_cml_ids_are_unique_across_the_files_given(tmp_path: Path) -> None:
    first = tmp_path / "A.cml"
    first.write_text("// id: ctx-a\nBoundedContext A {\n}\n")
    second = tmp_path / "Other.cml"
    second.write_text("BoundedContext A {\n}\n")
    assert main([str(first), str(second)]) == 1
    assert "// id: ctx-a-2" in second.read_text()
    assert first.read_text() == "// id: ctx-a\nBoundedContext A {\n}\n"
