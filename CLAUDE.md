# miserable-stamp

The **public**, Apache-2.0 pre-commit hook and Python package that inserts missing ids for
miserable. Everything in this repository, including this file, is visible to anyone.

## Keep it public-safe

- This repository may contain only **id insertion** and **format documentation** for tenants.
  Nothing about how miserable indexes, hashes, checks, triages or hosts anything belongs here:
  no hashing, no lint rules, no link logic, no service details. That code is proprietary and lives
  in the private `miserable-code` repository (its decision 0005).
- Do not reference private repositories' file contents, decision records or infrastructure here.

## Rules the code must keep

- Only ever **add** ids; never change an existing id or any other line. The only exception is
  moving a docstring's closing quotes after an inserted `@id` line.
- Idempotent: a second run changes nothing.
- Deterministic for a seeded `random.Random`, which tests always pass.
- Files that do not parse are left untouched.
- `tree-sitter` and `tree-sitter-python` stay pinned to the same versions as `miserable-code`.
  `miserable-code` depends on this package, and the two must resolve together.

## Work

- Test first, one PR per change; `main` is protected and merged by squash.
- Commands: `uv sync`, `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy`.
- Releases are tags `vX.Y.Z`. `miserable-code` pins a tag. Publishing to PyPI comes later, before the
  first external tenant.
