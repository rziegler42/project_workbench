# The action-review engine reads the review setting

Status: Proposed

## Context

Decision 5 of `2026-10-22-model-calls-go-through-vendor-bridges` says each engine reads "a file named for the engine,
`.workbench/<engine module>.json`, with a format number". The spec `action-review.md` followed it and designed
`.workbench/action-review.json`. The review engine already reads `.workbench/review.json` for the same three things, the
bridge, the model and the effort.

On 2026-10-26 the owner chose that the action-review engine reads `.workbench/review.json` and not a file of its own, and
approved the plan `2026-10-26-action-review-engine` on that basis. Increment A of that plan wrote the choice into
`action-review.md`, which now says it departs from decision 5. A decision outranks a spec, so the departure needs a record
of its own. This record is that record. It changes nothing else in decision 5.

## Decision

1. The action-review engine reads the project setting `.workbench/review.json`, the file the review engine reads, and
   not `.workbench/action-review.json`. It uses the reader the review engine uses: a file of at most 4,096 bytes, strict
   JSON, `format` 1, a required `bridge`, and an optional `model` and `effort`, with no default bridge.
2. The rest of decision 5 stands for this engine: the setting is a request and never an authorization, only an installed,
   pinned module that provides `model-bridge` runs, a bridge that is not is refused and no other vendor is tried, and
   the owner's personal setting is authoritative once it can be read. That setting is not built for either engine, so
   the engine reads the project file only. This is a recorded limit of both engines.
3. The rule "a file named for the engine" is relaxed for the two engines that ask a model for a review: they may share
   one file. A new engine names its own file unless the owner decides otherwise in a record.

## Alternatives considered

- **`.workbench/action-review.json`, as decision 5 reads.** It keeps the rule without an exception and lets each engine
  have its own bridge or model. Rejected by the owner: two files would hold the same three values for the same project,
  and the owner wants one place to change them.
- **A shared name for every engine from now on.** Rejected: it widens the exception to engines that do not exist and
  whose needs are unknown.

## Consequences

- One file sets the bridge, model and effort for both engines, and a change to it is one difference for `wb acknowledge`.
- Both readers refuse an unknown field, so a field added for one engine is refused by the other until both readers change
  together. The two engines cannot use different bridges or models in one project.
- The module `action-review` and the module `review-engine` now depend on the same setting format, so a change of format
  is a change to both.
- Decision 5 is not edited. If this record is accepted, its index row names it as refining decision 5 for this file name.
- Until it is accepted, `action-review.md` contradicts decision 5 on this one point, as the spec says.

## Evidence

Read on 2026-10-26 at commit `040798e` (working tree, nothing run): decision 5 of
`2026-10-22-model-calls-go-through-vendor-bridges`, `read_setting` in `packages/workbench/review-engine/helper/review-engine`
(4,096 bytes, strict JSON, `format` 1, `bridge` required, `model` and `effort` optional, no default bridge), and the
"Settings and the bridge" section of `docs/specs/action-review.md`. The `reviewer` agent found the conflict with
decision 5 in Increment A of the plan. The conclusion is that the choice contradicts the decision's file name and needs
this record.
