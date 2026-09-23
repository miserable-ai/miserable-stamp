# Tenant guide: markers and ids

This guide describes the text miserable reads from your repositories. Everything miserable does with
it happens in miserable's cloud. Your repositories need nothing but these formats, and optionally
the `miserable-stamp` hook.

## Code markers

Code declares its links with **markers** in the documentation of a symbol: a Python docstring, a
JSDoc or KDoc block, Swift `///` lines, or `#` comments directly above a Terraform block.

```
@relation(<UID>[, <UID>...], role=Implements)    the symbol implements these software requirements
@relation(<UID>[, <UID>...], role=Verifies)      the test verifies these acceptance criteria
@model(<model id>[, <model id>...], role=Implements)   the symbol implements these model elements
@id c-<10 characters>                            the symbol's stable identity
```

- Put one marker per line. Before a marker there may only be whitespace and the comment syntax `*`,
  `#` or `///`; after it, nothing.
- UIDs name requirements (`SR-20`) and acceptance criteria (`AC-201`). Model ids name elements of
  your architecture (`agg-sensor-node`).
- `role=Verifies` goes only on tests, and names acceptance criteria, not requirements.
- Every symbol that carries `@relation` or `@model` needs exactly one `@id`. `miserable-stamp`
  adds it. **Never edit or copy an `@id` line**: it is how miserable recognises the symbol after a
  rename or a move.
- A marker anywhere else, such as a comment inside a function body, is an error.

Example (Python):

```python
def check_battery(level: int) -> None:
    """Raise the low-battery alert.

    @relation(SR-20, role=Implements)
    @model(agg-sensor-node, role=Implements)
    @id c-7f3a9k2m1q
    """
```

## Specification ids (StrictDoc)

Every user requirement, software requirement, acceptance criterion and ADR carries a `MID:` field of
32 lower-case hex characters, directly after its element tag. The MID is the element's identity; the
UID (`SR-20`) is a readable name that may change. `miserable-stamp` adds missing MIDs. **Never edit or
copy a `MID:` line.**

## Model ids (Context Mapper)

Every CML element carries `// id: <id>` in the comment lines directly above its declaration, with no
blank line in between:

```
// id: agg-sensor-node
Aggregate SensorNode {
```

- An id is a kind prefix and a lower-case name: `dom-` domain, `sub-` subdomain, `ctx-` bounded
  context, `agg-` aggregate, `ent-` entity, `vo-` value object, `ev-` domain event, `cmd-` command
  event, `svc-` service, `enum-` enum, `uc-` use case, `us-` user story.
- Ids are unique across the repository, and **never changed after they are written**, even when the
  element is renamed. `miserable-stamp` adds missing ids.
- Use cases and user stories name the requirements they realise with `// from: SR-20, SR-21` in the
  same comment lines. No other element carries `// from:`.
- Each `.cml` file imports the files it references, as well as `ContextMap.cml` importing every
  file.
