"""`miserable-stamp FILE...`: add missing ids to the given files.

Meant to run as a pre-commit hook. It prints each file it changed and exits 1 when it changed any,
so the commit stops and the stamped files can be reviewed and staged. Files of other types are
ignored. A directory stands for every file under it, outside hidden directories; a path that does
not exist is refused with exit code 2, before anything is stamped.
"""

import random
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from miserable_stamp import dsl
from miserable_stamp.cml import existing_ids, stamp_cml
from miserable_stamp.code import language_for, stamp_code
from miserable_stamp.python import stamp_python
from miserable_stamp.sdoc import stamp_sdoc


def main(paths: Sequence[str], rng: random.Random | None = None) -> int:
    rng = rng or random.SystemRandom()
    missing = [p for p in paths if not Path(p).exists()]
    if missing:
        for name in missing:
            print(f"miserable-stamp: no such file or directory: {name}", file=sys.stderr)
        return 2
    paths = _expand(paths)
    model_ids = _model_ids([Path(p) for p in paths])
    deployment = _Deployment([Path(p) for p in paths])
    changed = 0
    for name in paths:
        path = Path(name)
        if not path.is_file():
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            before = handle.read()
        after = _stamp(path, before, rng, model_ids, deployment)
        if after is not None and after != before:
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write(after)
            print(f"stamped {name}")
            changed += 1
    return 1 if changed else 0


def _expand(paths: Sequence[str]) -> list[str]:
    """`paths` with each directory replaced by the files under it, outside hidden directories."""
    out: list[str] = []
    for name in paths:
        path = Path(name)
        if not path.is_dir():
            out.append(name)
            continue
        for child in sorted(path.rglob("*")):
            hidden = any(part.startswith(".") for part in child.relative_to(path).parts)
            if child.is_file() and not hidden:
                out.append(str(child))
    return out


def _stamp(
    path: Path, text: str, rng: random.Random, model_ids: set[str], deployment: "_Deployment"
) -> str | None:
    if path.suffix == ".py":
        return stamp_python(text, rng)
    if path.suffix == ".sdoc":
        return stamp_sdoc(text, rng)
    if path.suffix == ".cml":
        return stamp_cml(text, model_ids)
    if path.suffix == ".dsl":
        return dsl.stamp_dsl(text, deployment.ids, deployment.names)
    language = language_for(path.name)
    if language is not None:
        return stamp_code(text, language, rng)
    return None


def _model_ids(paths: list[Path]) -> set[str]:
    """Ids already used by CML files (ids must be unique across the whole model)."""
    ids: set[str] = set()
    for text in _repository_texts(paths, ".cml"):
        ids |= existing_ids(text)
    return ids


class _Deployment:
    """What the repository's Structurizr DSL files hold: the `miserable.id` values in use, which
    must stay unique across them, and the names of the elements their identifiers define."""

    def __init__(self, paths: list[Path]) -> None:
        self.ids: set[str] = set()
        self.names: dict[str, str] = {}
        for text in _repository_texts(paths, ".dsl"):
            self.ids |= dsl.existing_ids(text)
            for identifier, name in dsl.element_names(text).items():
                self.names.setdefault(identifier, name)


def _repository_texts(paths: list[Path], suffix: str) -> list[str]:
    """The text of every tracked file of the repository with `suffix`, plus the files given with
    it (pre-commit passes only staged files), in a stable order."""
    files = {p for p in paths if p.suffix == suffix and p.is_file()}
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", f"*{suffix}"], capture_output=True, check=False
    )
    if result.returncode == 0:
        files |= {Path(p) for p in result.stdout.decode().split("\0") if p}
    return [p.read_text(encoding="utf-8") for p in sorted(files) if p.is_file()]


def main_entry() -> None:
    sys.exit(main(sys.argv[1:]))
