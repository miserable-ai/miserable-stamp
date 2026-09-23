"""`miserable-stamp FILE...`: add missing ids to the given files.

Meant to run as a pre-commit hook. It prints each file it changed and exits 1 when it changed any,
so the commit stops and the stamped files can be reviewed and staged. Files of other types are
ignored.
"""

import random
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from miserable_stamp.python import stamp_python
from miserable_stamp.sdoc import stamp_sdoc

_STAMPERS: dict[str, Callable[[str, random.Random], str]] = {
    ".py": stamp_python,
    ".sdoc": stamp_sdoc,
}


def main(paths: Sequence[str], rng: random.Random | None = None) -> int:
    rng = rng or random.SystemRandom()
    changed = 0
    for name in paths:
        path = Path(name)
        stamper = _STAMPERS.get(path.suffix)
        if stamper is None or not path.is_file():
            continue
        with path.open(encoding="utf-8", newline="") as handle:
            before = handle.read()
        after = stamper(before, rng)
        if after != before:
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write(after)
            print(f"stamped {name}")
            changed += 1
    return 1 if changed else 0


def main_entry() -> None:
    sys.exit(main(sys.argv[1:]))
