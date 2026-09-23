"""`miserable-stamp FILE...`: add missing ids to the given files.

Meant to run as a pre-commit hook. It prints each file it changed and exits 1 when it changed any,
so the commit stops and the stamped files can be reviewed and staged. Files of other types are
ignored.
"""

import random
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from miserable_stamp.cml import existing_ids, stamp_cml
from miserable_stamp.python import stamp_python
from miserable_stamp.sdoc import stamp_sdoc


def main(paths: Sequence[str], rng: random.Random | None = None) -> int:
    rng = rng or random.SystemRandom()
    model_ids = _model_ids([Path(p) for p in paths])
    changed = 0
    for name in paths:
        path = Path(name)
        if not path.is_file():
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            before = handle.read()
        after = _stamp(path, before, rng, model_ids)
        if after is not None and after != before:
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write(after)
            print(f"stamped {name}")
            changed += 1
    return 1 if changed else 0


def _stamp(path: Path, text: str, rng: random.Random, model_ids: set[str]) -> str | None:
    if path.suffix == ".py":
        return stamp_python(text, rng)
    if path.suffix == ".sdoc":
        return stamp_sdoc(text, rng)
    if path.suffix == ".cml":
        return stamp_cml(text, model_ids)
    return None


def _model_ids(paths: list[Path]) -> set[str]:
    """Ids already used by CML files: every tracked model file of the repository, plus those given
    (pre-commit passes only staged files, but ids must be unique across the whole model)."""
    files = {p for p in paths if p.suffix == ".cml" and p.is_file()}
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "*.cml"], capture_output=True, check=False
    )
    if result.returncode == 0:
        files |= {Path(p) for p in result.stdout.decode().split("\0") if p}
    ids: set[str] = set()
    for path in files:
        if path.is_file():
            ids |= existing_ids(path.read_text(encoding="utf-8"))
    return ids


def main_entry() -> None:
    sys.exit(main(sys.argv[1:]))
