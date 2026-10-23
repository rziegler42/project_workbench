# Apply the edit gate's 64 KiB input bound only while a plan is under way

Status: Completed
Created: 2026-10-23
Candidate: none (a change the owner chose to a limit recorded in the plan `2026-10-22-checkpoint-settings-and-caps`)
Specs: trust-and-approval

## Goal

With the hook installed, `wb gate` today refuses any tool call whose input is over 65,536 bytes, before it looks at
the project. A `Write` of more than about 64 KiB is therefore refused even when no plan is under way and the gate has
nothing to guard. The owner has chosen to skip the bound in that case.

When this plan is done:

- a tool call with a large input is allowed when no plan is under way (and when the project has no process module
  that declares `approval.active`), as any other call is;
- while a plan is under way the 64 KiB bound still refuses a call, so the gate's input to its placement and approval
  checks is as bounded as before;
- the read is still bounded, by a larger limit that applies always and fails closed;
- `trust-and-approval.md` says this, and the sentence that called it "the owner's call" is gone.

## Scope

- `workbench/gate_hook.py`: a larger read limit, and the 64 KiB check moved to after the plans under way are known
  (increment A). The tests in `tests/test_gate_hook.py` (increment A).
- The spec sentence and the plan record (increment B).

## Non-goals

- Any change to what the gate decides once a plan is under way, to the placement of a target, or to the deadline.
- A guard for the settings file when no plan is under way (see the plan `2026-10-22-absolute-settings-deny`,
  Deferred work).
- Any change to a module, to the harness layout, or to a shipped approval. Nothing under `packages/` changes, so no
  release is expected.

## Assumptions and constraints

- Python standard library only; tests with `unittest`; the full suite is `python3 -B -W error tests/run_all.py`.
- `workbench/` and `tests/` name no first-party module, helper or path (`tests/test_boundary.py`).
- The input is read before the project is known, because the project is found from `cwd` inside the input. To decide
  that no plan is under way, the gate must parse an input of any size up to the new read limit.
- `jsonstrict.parse_object(data, limit)` refuses data over `limit` and checks depth; it is given the new limit.
- The total deadline of 10 seconds covers the read and the parse.
- Discovery tooling: graphify: skipped — not installed in this project; the scope was found by reading
  `workbench/gate_hook.py`, `tests/test_gate_hook.py` and `docs/specs/trust-and-approval.md`.

### Choices (made by me; the owner may change any)

1. **A transport limit of 16 MiB, always applied.** An input over it is refused whether or not a plan is under way. The
   alternative, no limit, would read without bound from the harness. Cost: a `Write` of more than 16 MiB is refused with
   the hook installed. The number is mine.
2. **While a plan is under way the existing bound of 65,536 bytes still refuses,** with the message the gate gives today.
   The alternative, lifting it for those calls too, was not asked for and would widen what the placement checks see.
3. **The check happens in `decide`,** after `active` returns plans, so a project with no gate module, a failed
   `active`, and a project with no plan under way keep their current outcomes, and only the size rule moves.
4. **`decide` gets the size as an argument** with a default of zero, so a direct call in a test that does not pass it
   behaves as before.

## Completion criteria

1. A call whose input is over 65,536 bytes and within 16 MiB is allowed when no plan is under way, and refused, with
   the existing wording, when one is. A call over 16 MiB is refused in both cases.
2. An input of exactly 65,536 bytes is read and decided as today, and one byte more is refused only while a plan is
   under way.
3. A malformed, deeply nested or non-UTF-8 large input is refused as a small one is.
4. The deadline still ends a slow read or parse in a refusal.
5. The full suite and the boundary test pass; `trust-and-approval.md` no longer says the bound applies with no plan
   under way; `doccheck`, `refcheck` and `git diff --check` print nothing.

## Increments

### Increment A — Apply the bound only while a plan is under way

**Outcome:** a large input is allowed when nothing is under way and refused when a plan is.
**Dependencies:** none.
**Affected areas:** `workbench/gate_hook.py` (`MAX_INPUT`, `_read`, `decide`, `run`), `tests/test_gate_hook.py`.
**Steps:**
1. Test first, in `tests/test_gate_hook.py`: replace `test_input_over_the_bound_is_refused_and_input_at_it_is_read` with
   tests for each case of criteria 1 to 4 — large input with no plan under way (allowed), the same with a plan under way
   (refused, message names 65536), input at 65,536 bytes and one byte over in both states, an input over the transport
   limit (refused in both states), and a large input that is nested too deeply, is not UTF-8 or is not an object
   (refused). Run them and see them fail.
2. Add `MAX_TRANSPORT = 16 * 1024 * 1024` beside `MAX_INPUT`. `_read` reads `MAX_TRANSPORT + 1` bytes, parses with
   `MAX_TRANSPORT`, and returns the size of the input beside `cwd`, `tool` and `given`; the refusal for an input over the
   transport limit names that limit.
3. `decide` takes `size=0`. After `plans` is known and non-empty, and before the target is read, it raises the existing
   refusal when `size > MAX_INPUT`. `run` passes the size.
4. Update the module docstring (item 1) to match.
**Verification:** the new tests; `python3 -B -W error -m unittest tests.test_gate_hook`; the boundary test.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-gate-input-bound-only-under-way#A`.

### Increment B — Spec and record

**Outcome:** the spec says what is built, and the plan records it.
**Dependencies:** A.
**Affected areas:** `docs/specs/trust-and-approval.md` ("`wb gate <harness>`" and its "Limits"), this plan's Result,
`docs/plans/2026-10-22-checkpoint-settings-and-caps.md` only if its Result needs a pointer (status, review record and
result are the only parts that may change).
**Steps:**
1. In the spec, the input sentence says at most 16 MiB is read, and the 65,536 byte bound applies while a plan is
   under way; remove the sentence that skipping the bound "would change this spec and is the owner's call".
2. Run the full suite, `doccheck`, `refcheck` and `git diff --check`.
3. Fill the Result.
**Verification:** the document checks print nothing; the full suite passes; a search finds no document that says the
bound applies when no plan is under way.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-gate-input-bound-only-under-way#B`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots, with no Claude skip; `git diff --check` and the document
  checks print nothing.
- No live recheck is planned: the change is in a path a test exercises with a fake input, and the live behaviour of
  the hook is unchanged. The owner may ask for one.

## Risks and sensitive actions

- **A larger parse before the gate knows it has nothing to do.** Up to 16 MiB of JSON is parsed on every call that has
  a large input. The input comes from the harness, not from a plan or a repository file, and the deadline bounds the
  time. A security pass over the read and parse is part of review if the owner asks for one. Reviews run only when the
  owner asks.
- **The change loosens a fail-closed rule.** It does so only when no plan is under way, where the gate allows every
  call anyway; the order of checks is what changes, not what the gate permits.
- Nothing is pushed by this plan. No approval release is expected; if a test shows otherwise it runs only on the
  owner's exact words.

## Review record

Empty until a review is asked for.

## Deferred work

- A guard for the settings file that does not depend on a plan being under way.
- A transport limit that the owner can set, in the layout or the settings file, if 16 MiB is wrong for a harness.

## Result

Done on 2026-10-23.

- Increment A (`4cfe623`): `workbench/gate_hook.py` reads at most `MAX_TRANSPORT` (16 MiB) and refuses more in every
  state. The 65,536 byte bound is checked in `decide` only after `active` reports a plan under way. New tests in
  `tests/test_gate_hook.py` failed before the change and pass after it.
- Increment B: `trust-and-approval.md` ("`wb gate <harness>`" and "Limits") now says this, and the sentence that
  called skipping the bound "the owner's call" is gone. A search of `docs` finds no current document that says the
  bound applies with no plan under way; older plans keep their own wording as history.
- Verification: `python3 -B -W error tests/run_all.py` ran 3087 tests in 6 roots, OK (installer 2337 with 1
  skipped, ask-codex 90, claude 32 with no skips, code-work 220 with 2 skipped, groundwork 178, safe-git 230);
  `doccheck`, `refcheck` and `git diff --check` print nothing. Nothing under `packages/` changed, so no approval
  release was needed.
- Not explained: the gate test module stalled once, around its 24th test, during increment A, and was stopped by
  hand. Reruns of that module and of the full suite passed. The cause was not found; investigate if it recurs.
- Not done: no live recheck and no independent security review of the read and parse path (both only if the owner
  asks). Nothing is pushed.
