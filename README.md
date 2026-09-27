# miserable-stamp

A small [pre-commit](https://pre-commit.com/) hook that gives every traceable item in your
repository a stable id, so that [miserable](https://miserable.ai) can keep your specification,
architecture and code linked.

It only ever **adds** ids. It never changes an existing id and never touches anything else in a
file.

| file | what it adds |
| --- | --- |
| Python (`.py`) | `@id c-xxxxxxxxxx` in the docstring of every function or class that carries `@relation(...)` or `@model(...)` but no `@id` yet |
| Kotlin (`.kt`, `.kts`) | `@id c-xxxxxxxxxx` in the KDoc `/** */` above every function, class, object or interface that carries `@relation(...)` or `@model(...)` but no `@id` yet |
| Java (`.java`) | the same in the Javadoc `/** */` above every class, interface, enum, record, constructor or method |
| TypeScript (`.ts`, `.tsx`, `.mts`, `.cts`) | the same in the JSDoc `/** */` above every function or class declaration, method, exported `const` arrow function, and `it(...)` or `test(...)` call; above `export` when the declaration is exported |
| Swift (`.swift`) | the same in the `///` lines or `/** */` block above every `func`, `class`, `struct`, `enum` or `protocol`, and every member of an `extension` |
| Terraform (`.tf`, `.tftest.hcl`) | the same in the `#` or `//` comment lines above every top-level `resource`, `module` or `data` block, and every `run` block of a `.tftest.hcl` file |
| StrictDoc (`.sdoc`) | `MID: <32 hex characters>` directly after the tag of every `USER_REQUIREMENT`, `REQUIREMENT`, `ACCEPTANCE_CRITERION` and `ADR` without one |
| Context Mapper (`.cml`) | `// id: <prefix>-<name>` directly above every domain, subdomain, bounded context, aggregate, entity, value object, event, service, enum, use case and user story without one, unique across the repository's models |

Support for more languages will follow.

## Use it

Add it to your repository's `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/miserable-ai/miserable-stamp
    rev: v0.2.0
    hooks:
      - id: miserable-stamp
```

When the hook adds ids, the commit stops and lists the stamped files. Review them, `git add` them
and commit again. Running it twice changes nothing.

You can also run it by hand:

```sh
uvx --from git+https://github.com/miserable-ai/miserable-stamp@v0.2.0 miserable-stamp path/to/file.py
```

The hook is a convenience. If a commit reaches miserable without ids, miserable adds them for you
on the pull request branch, for pull requests from branches of your repository. It cannot push to
forks, so a pull request from a fork needs the ids committed before it is merged.

## Formats

[docs/tenant-guide.md](docs/tenant-guide.md) describes the markers and ids miserable reads.

## Development

```sh
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

## Licence

Apache License 2.0; see [LICENSE](LICENSE).
