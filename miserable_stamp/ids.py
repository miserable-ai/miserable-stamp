"""New ids in the formats miserable expects."""

import random
import uuid

CROCKFORD_LOWER = "0123456789abcdefghjkmnpqrstvwxyz"


def new_code_id(rng: random.Random, taken: set[str]) -> str:
    """`c-` and ten lower-case Crockford characters, not in `taken` (which it is added to)."""
    while True:
        candidate = "c-" + "".join(rng.choice(CROCKFORD_LOWER) for _ in range(10))
        if candidate not in taken:
            taken.add(candidate)
            return candidate


def new_mid(rng: random.Random, taken: set[str]) -> str:
    """A StrictDoc MID: a random UUID4 as 32 lower-case hex characters, not in `taken`."""
    while True:
        candidate = uuid.UUID(int=rng.getrandbits(128), version=4).hex
        if candidate not in taken:
            taken.add(candidate)
            return candidate
