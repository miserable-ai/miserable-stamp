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

- Only ever **add** ids; never change an existing id or any other line. The only exceptions are
  moving a docstring's closing quotes, or a comment block's closing `*/`, after an inserted `@id`
  line, and opening the braces of a Structurizr DSL element that has none (or only `{}`) so that
  its new `properties` block has somewhere to go.
- Idempotent: a second run changes nothing.
- Deterministic for a seeded `random.Random`, which tests always pass.
- Files that do not parse are left untouched. For code, that means a node reachable through the
  parse tree's children that is an `ERROR` or a `MISSING` node. A hidden `MISSING` node, which
  tree-sitter-kotlin inserts into some valid one-liners, is not reachable and does not count. For
  Swift only an `ERROR` node counts: tree-sitter-swift inserts visible `MISSING` nodes into valid
  code (`@Option() var x`, `.success(())`). C is judged per definition: a function, struct, union
  or enum definition holding an `ERROR` or `MISSING` node is left unstamped, and the file's other
  definitions are stamped, since tree-sitter-c cannot expand macros and most real C files hold some
  parse error outside the definitions that carry markers.
- `tree-sitter` and every `tree-sitter-<language>` grammar stay pinned to exactly the same versions
  as `miserable-code`. `miserable-code` depends on this package, and the two must resolve together.

## Work

- Test first, one PR per change; `main` is protected and merged by squash.
- Commands: `uv sync`, `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy`.
- Releases are tags `vX.Y.Z`. `miserable-code` pins a tag. Publishing to PyPI comes later, before the
  first external tenant.
