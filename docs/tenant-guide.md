# Tenant guide: markers and ids

This guide describes the text miserable reads from your repositories. Everything miserable does with
it happens in miserable's cloud. Your repositories need nothing but these formats, optionally the
`miserable-stamp` hook, and in code repositories two CI artifacts (see "Test results and coverage").

## Code markers

Code declares its links with **markers** in the documentation of a symbol. In Python that is the
docstring. In every other language it is the unbroken run of comments directly above the
declaration: a blank line ends the run, and a comment inside a body never counts.

| language | files | documentation | symbols that carry markers |
| --- | --- | --- | --- |
| Python | `.py` | the docstring | functions, methods, classes |
| Kotlin | `.kt`, `.kts` | KDoc `/** */` above the declaration and its annotations | `fun`, `class`, `data class`, `enum class`, `object`, `interface`, members of a `companion object` |
| Java | `.java` | Javadoc `/** */` above the declaration and its annotations | classes, interfaces, enums, records, constructors, methods |
| TypeScript | `.ts`, `.tsx`, `.mts`, `.cts` | JSDoc `/** */` above the declaration, above `export` when it is exported, and above a method's decorators; a test call only by a JSDoc block | function and class declarations and overload signatures, methods and a class's overload signatures, exported `const` arrow functions, and `it(...)` / `test(...)` calls with a callback in tests, also as `.only`, `.skip` and `.each` |
| Swift | `.swift` | a run of `///` lines, or one `/** */` block, above the declaration and its attributes | `func`, `class`, `struct`, `enum`, `protocol`, members of an `extension` |
| Terraform | `.tf`, `.tftest.hcl` | a run of `#` or `//` lines above the block | top-level `resource`, `module` and `data` blocks; `run` blocks in `.tftest.hcl` files |
| C | `.c`, `.h` | a `/** */` or `/* */` block, or a run of `//` lines, above the definition, or above the `typedef` holding a type | function definitions, and `struct`, `union` and `enum` definitions with a body, at file scope (also inside `#if` blocks and `extern "C"`); not prototypes. A definition the parser cannot read, often because of a macro it cannot expand, gets no id |

The markers:

```
@relation(<UID>[, <UID>...], role=Implements)    the symbol implements these software requirements
@relation(<UID>[, <UID>...], role=Verifies)      the test verifies these acceptance criteria
@model(<model id>[, <model id>...], role=Implements)   the symbol implements these model elements
@id c-<10 characters>                            the symbol's stable identity
```

- Put one marker per line. Before a marker there may only be whitespace and the comment syntax
  `/**`, `*`, `///`, `//` or `#`; after it, nothing but the closing `*/` of a block.
- UIDs name requirements (`SR-20`) and acceptance criteria (`AC-201`). Model ids name elements of
  your architecture (`agg-sensor-node`) or of your deployment (`dep-monitoring-api`).
- `role=Verifies` goes only on tests, and names acceptance criteria, not requirements.
- Every symbol that carries `@relation` or `@model` needs exactly one `@id`. `miserable-stamp`
  adds it as a new line after the last marker, in the same comment style. When a `/** */` block
  closes on the marker's line, the closing `*/` moves to the end of the new line. **Never edit or
  copy an `@id` line**: it is how miserable recognises the symbol after a rename or a move.
- A marker anywhere else, such as a comment inside a function body, is an error.

Python:

```python
def check_battery(level: int) -> None:
    """Raise the low-battery alert.

    @relation(SR-20, role=Implements)
    @model(agg-sensor-node, role=Implements)
    @id c-7f3a9k2m1q
    """
```

Kotlin (Java and TypeScript alike, with their own annotations or decorators below the block):

```kotlin
/**
 * Raises the low-battery alert.
 *
 * @relation(SR-20, role=Implements)
 * @id c-7f3a9k2m1q
 */
@Throws(IllegalStateException::class)
fun checkBattery(level: Int) {
```

TypeScript, exported and in a test:

```typescript
/**
 * @relation(SR-20, role=Implements)
 * @id c-7f3a9k2m1q
 */
export function checkBattery(level: number): void {

/**
 * @relation(AC-201, role=Verifies)
 * @id c-2b8r0d4w6x
 */
it("raises the alert below 20", () => {
```

Swift:

```swift
/// Raises the low-battery alert.
/// @relation(SR-20, role=Implements)
/// @id c-7f3a9k2m1q
func checkBattery(level: Int) {
```

Terraform:

```hcl
# The monitoring function.
# @model(dep-monitoring-api, role=Implements)
# @id c-7f3a9k2m1q
resource "aws_lambda_function" "monitoring" {
```

C:

```c
/**
 * Raises the low-battery alert.
 * @relation(SR-20, role=Implements)
 * @id c-7f3a9k2m1q
 */
int check_battery(int level)
{
```

## Specification ids (StrictDoc)

Every user requirement, software requirement, acceptance criterion, ADR and risk-file element
(hazard, hazardous situation, harm, cause, risk, risk control measure, threat, item class) carries a
`MID:` field of 32 lower-case hex characters, directly after its element tag. The MID is the
element's identity; the UID (`SR-20`) is a readable name that may change. `miserable-stamp` adds
missing MIDs. **Never edit or copy a `MID:` line.**

## Model ids (Context Mapper)

Every CML element carries `// id: <id>` in the comment lines directly above its declaration, with no
blank line in between:

```
// id: agg-sensor-node
Aggregate SensorNode {
```

- An id is a kind prefix and a lower-case name: `dom-` domain, `sub-` subdomain, `ctx-` bounded
  context, `agg-` aggregate, `ent-` entity, `vo-` value object, `ev-` domain event, `cmd-` command
  event, `svc-` service, `repo-` repository (declared in an aggregate root; its id leaves out the
  name's `Repository` suffix, so `LandingRecordRepository` is `repo-landing-record`), `enum-` enum,
  `uc-` use case, `us-` user story.
- Ids are unique across the repository, and **never changed after they are written**, even when the
  element is renamed. `miserable-stamp` adds missing ids.
- Use cases and user stories name the requirements they realise with `// from: SR-20, SR-21` in the
  same comment lines. No other element carries `// from:`.
- Each `.cml` file imports the files it references, as well as `ContextMap.cml` importing every
  file.

## Deployment ids (Structurizr DSL)

In a deployment architecture written in the Structurizr DSL, every `deploymentNode`,
`infrastructureNode`, `containerInstance` and `softwareSystemInstance` carries a `miserable.id`
property in its own `properties` block:

```
deploymentNode "Amazon Web Services" {
    properties {
        "miserable.id" "dep-amazon-web-services"
    }

    containerInstance api {
        properties {
            "miserable.id" "dep-monitoring-api"
        }
    }
}
```

- An id is `dep-` and a lower-case name: the element's name, and for an instance the name of the
  container or software system it instantiates.
- Ids are unique across the repository's `.dsl` files, and **never changed after they are
  written**, even when the element is renamed. `miserable-stamp` adds missing ids: it creates the
  `properties` block, and opens the element's braces, where they are missing.
- Write the workspace in DSL, not as `workspace.json`.
- Keep the workspace in a directory of its own, for example `deployment/workspace.dsl`, and name
  that root file in `product.yaml` as the deployment's `workspace` (default `workspace.dsl`). Only
  the root and the files its `!include`s reach are read; an `!include` must be a relative path
  inside that directory, without `..`.

## Requirement forms (specification repositories)

miserable can check that each requirement takes its sentence form: a user requirement is a need
statement ("the clinician needs …"), a software requirement follows EARS ("When …, the pump shall
…"), and an acceptance criterion verified by test is one Gherkin `Scenario`. You choose how strictly,
per kind, under `config.spec.forms` in `product.yaml`:

| mode | a new or changed statement | an untouched statement |
| --- | --- | --- |
| `off` | not checked | not checked |
| `warn` (default) | warnings | warnings |
| `changed` | errors | warnings |
| `strict` | errors | errors |

```yaml
config:
  spec:
    forms:
      ur: { mode: changed }
      sr: { mode: changed }
      ac: { mode: changed }
```

When you switch the forms on, start with **`changed`**: every statement you write or edit from then
on must take its form, while existing statements only warn, so no pull request fails for a statement
it did not touch. Move to `strict` once the existing statements are in form.

## Test results and coverage (code repositories)

miserable reads your CI's test results to tell which acceptance criteria your tests verify and
whether they pass. Your CI runs only your own tests. It uploads two artifacts from one workflow,
the one `product.yaml` names under `ci.workflow` (default `ci.yml`):

| artifact (default name) | setting in `product.yaml` | content |
| --- | --- | --- |
| `miserable-junit` | `ci.junit_artifact` | JUnit XML reports (`*.xml`) |
| `miserable-exercises` | `ci.exercises_artifact` | the raw coverage.py data file `.coverage`, recorded with per-test contexts |

For Python with pytest:

```yaml
      - run: pip install pytest pytest-cov
      - run: python -m pytest --junitxml=junit.xml --cov=. --cov-context=test tests
      - uses: actions/upload-artifact@v7
        if: always()
        with:
          name: miserable-junit
          path: junit.xml
      - uses: actions/upload-artifact@v7
        if: always()
        with:
          name: miserable-exercises
          path: .coverage
          include-hidden-files: true
```

- `python -m pytest` puts the checkout on the import path, so your tests can import your package.
- `--cov-context=test` records which test ran each line. Without it, miserable knows the results
  but not what each test exercised.
- `include-hidden-files: true` is needed because `.coverage` starts with a dot.
- `if: always()` uploads the results when a test fails too: failures are what miserable reports.
- Upload the raw `.coverage` file, not a report: miserable converts it itself.

For TypeScript, upload the JUnit XML of your test runner as `miserable-junit` (there is no coverage
artifact):

- **Vitest:** `vitest run --reporter=junit --outputFile=junit.xml`, run with the repository's root
  as Vitest's root, so that each case's file is the file's path in the repository.
- **Jest:** the `jest-junit` reporter, configured with `classNameTemplate: "{classname}"`,
  `titleTemplate: "{title}"`, `ancestorSeparator: " > "` and `addFileAttribute: "true"`, with Jest's
  `rootDir` at the repository's root. Its default names cannot be read.
- A `test.each` case matches its test by the title as written, placeholders (`%i`, `$level`)
  included.

## Work in progress: `git wip`

A **work in progress** (WIP) is a branch you push to show miserable your unfinished work without
opening a pull request: `wip/<your login>/<your branch>`, where the login is your GitHub login and
the branch is the one you have checked out (not the default branch). miserable reads it like any
other branch, lists it as yours and shows it to you first, and posts no checks on it. Open a pull
request from it and it becomes an ordinary branch, judged and checked like any other.

The recipe below pushes a snapshot of your working tree, staged or not and untracked files
included, without committing on your branch or touching what you have staged. Save it as a file,
for example `~/.config/git/wip.sh`:

```sh
# git_wip [--delete]: push the working tree to wip/<login>/<branch>, or delete that branch.
git_wip() (
  branch=$(git symbolic-ref --quiet --short HEAD) || {
    echo "git wip: detached HEAD; check out a branch first" >&2; exit 1; }
  login=$(git config miserable.login || gh api user -q .login) && [ -n "$login" ] || {
    echo "git wip: set your GitHub login with git config miserable.login" >&2; exit 1; }
  ref="refs/heads/wip/$login/$branch"
  if [ "${1-}" = "--delete" ]; then
    git push origin --delete "$ref"; exit
  fi
  cd "$(git rev-parse --show-toplevel)" || exit 1

  # Stamp missing ids in place, in every tracked or untracked file that is not gitignored.
  # miserable-stamp exits 1 when it stamped something, which xargs reports as 123.
  git ls-files -z -co --exclude-standard |
    xargs -0 -r sh -c 'for f; do [ -f "$f" ] && [ ! -L "$f" ] && printf "%s\0" "$f"; done' sh |
    xargs -0 -r miserable-stamp
  case $? in
    0 | 1 | 123) ;;
    *) echo "git wip: miserable-stamp failed; nothing pushed" >&2; exit 1 ;;
  esac

  # Snapshot through a temporary index, so your own index stays as it is.
  untracked=$(git ls-files -o --exclude-standard)
  GIT_INDEX_FILE="$(git rev-parse --absolute-git-dir)/wip-index"
  export GIT_INDEX_FILE
  rm -f "$GIT_INDEX_FILE"
  git read-tree HEAD && git add -A && tree=$(git write-tree) &&
    commit=$(git commit-tree -p HEAD -m "wip: $branch" "$tree")
  status=$?
  rm -f "$GIT_INDEX_FILE"
  unset GIT_INDEX_FILE
  [ "$status" -eq 0 ] || { echo "git wip: snapshot failed; nothing pushed" >&2; exit 1; }

  if [ -n "$untracked" ]; then
    echo "git wip: these untracked files are included; anything not gitignored is pushed (.env too):"
    printf '%s\n' "$untracked" | sed 's/^/  /'
  fi
  git push -f origin "$commit:$ref" && echo "git wip: pushed $branch to wip/$login/$branch"
)
```

Then make it a git command:

```sh
git config --global alias.wip '!f() { . ~/.config/git/wip.sh; git_wip "$@"; }; f'
```

- `git wip` stamps missing ids in your working tree, in place, as the hook would, and pushes the
  snapshot. Run it as often as you like: each run replaces the branch.
- `git wip --delete` deletes your WIP branch (the same as
  `git push origin --delete wip/<login>/<branch>`).
- Your login comes from `git config miserable.login`, or else from the GitHub CLI
  (`gh api user -q .login`).

Notes:

- Your CI need not run on WIP branches. To skip it, add `branches-ignore: ['wip/**']` under the
  `push` trigger of your workflows.
- If you protect branches with rulesets, they must allow pushing and force-pushing to `wip/**`.
- Never name a feature branch `wip/…`: that prefix is what makes a branch a WIP.
- Anyone who can read the repository can read your WIP, as with any branch on GitHub.

### Pin, then flip

A dependent repository pins its upstream in `trace.lock`. While you develop a change that spans
repositories, pin the upstream's branch of the same name instead of a release:

```yaml
upstream:
  spec: branch:add-dose-limits
```

When you push your WIP of the dependent, the pin `branch:add-dose-limits` prefers your own WIP of
the upstream, `wip/<your login>/add-dose-limits`, and falls back to `add-dose-limits` when you have
none. So your WIPs of several repositories are judged together, and pushing or deleting the
upstream WIP later re-evaluates the dependent ones. `trace.lock` itself is never rewritten.

At landing, merge and release the upstream first, then flip the pin to its release tag (for example
`spec: srs-v1.4.0`) in the dependent's pull request: on a default branch, the pin is a release tag.
