# Deny agent writes to the local harness manifest

Status: Proposed
Created: 2026-10-28
Candidate: none — a finding of the security review of Increment B of `2026-10-28-refresh-rendered-harness`, not a roadmap candidate
Specs: harness-refresh, command-permissions

## Goal

The edited-file test of `wb rerender` compares each rendered file with the hash recorded in the local manifest
(`.workbench/local/harness.json`). Whoever can write that manifest can record an edited file's hash, so the edit is
read as stale and replaced, or a changed file is read as `current` and never shown. After this plan the rendered
permissions deny the harness's write tool on the manifest, in the same spellings as the other protected files, so an
agent cannot write it.

## Scope

- `harnessstage.stage` passes the manifest's path (`localmanifest.PATH`) to `render_permissions` through the existing
  `protect` argument, beside the confined agents' files. Attach and rerender both render through `stage`, so both get it.
- Tests that show the deny is rendered in the three spellings, that attach and rerender render the same file, and that
  an existing clone sees it as a change of the permissions file in `wb preview rerender`.
- `docs/specs/harness-refresh.md` ("Limits as built") and `docs/specs/command-permissions.md` (the list of what is
  always denied) say it is built.

## Non-goals

- Corroborating each hash in the guarded store. That is a change of the manifest's format and stays an owner decision.
- The three Low findings of that review (non-atomic create, `.git/info/exclude`, line separators).
- Stopping a write by the shell. The deny covers the harness's write tool, as for the settings file and the hooks; the
  command gate's coverage of shell writes is unchanged.
- Any change to what `wb rerender` writes or to its states.

## Assumptions and constraints

- `protect` takes plain relative paths and renders them as `Edit(path)`, `Edit(**/path)` and `Edit(<root>/path)`
  (`harnessplan._spelled`). The manifest's path is plain.
- The installer's own writes go through its `Writer`, not the harness's tool, so the deny does not stop `wb attach`,
  `wb upgrade` or `wb rerender`.
- The deny reaches a clone only when its permissions file is rendered again. Until the owner runs `wb rerender` once, an
  existing clone lacks it; the preview shows it as a change of the permissions file.
- `workbench/` and `tests/` may not name a module, helper, harness or path other than the installer's own
  (`tests/test_boundary.py`); the manifest's path is the installer's.
- Nothing is run for security: no new dependency, no secret.

## Completion criteria

1. A permissions file rendered by attach or by rerender denies writes to `.workbench/local/harness.json` in the three
   spellings, when it renders at all.
2. A render without permissions (a harness that provides none) is unchanged.
3. `wb preview rerender` on a clone attached before this shows the permissions file as changed by exactly those rules.
4. The two specs state it; the full suite and `wb check` pass.

## Increments

### Increment A — Protect the local manifest in the rendered permissions

**Outcome:** every rendered permissions file denies the harness's write tool on the local manifest.
**Dependencies:** none.
**Affected areas:** `workbench/harnessstage.py`; tests that compare a rendered permissions file with an expected one
(`tests/test_hook_render.py` and any staged-file test the full suite shows red); `docs/specs/harness-refresh.md`;
`docs/specs/command-permissions.md`.
**Steps:**
1. Write the test first: a staged permissions file holds the three `Edit` denies for the manifest's path; see it fail.
2. In `harnessstage.stage`, pass `protect=tuple(done.confined) + (localmanifest.PATH,)` to `render_permissions`.
3. Make the tests that compare a whole rendered file expect the three added rules, and no other change.
4. Add a test that a rerender preview over a clone rendered without the rule lists the permissions file as changed and
   a second run after the write lists nothing.
5. Update the two specs: remove the finding from "Limits as built" as closed, and add the manifest to the always-denied
   files.
6. Record the Result in the plan.
**Verification:** the new tests red then green; `tests/test_hook_render.py` and the staging tests; `git diff --check`;
`wb check`; `wb run code-work check`; the full suite `python3 -B -W error tests/run_all.py`; a `reviewer` pass.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-28-protect-local-manifest#A`.

## Verification for the plan as a whole

The full suite, `wb check` and the plan check. In a scratch clone: attach, read the permissions file for the three denies,
edit the manifest with the harness's tool and see it refused (not possible to prove from the tests alone, so it is
recorded as not run if the scratch harness cannot be driven).

## Risks and sensitive actions

- The change is to what is rendered into an owner's permissions file, so it is security-relevant. It only adds `deny`
  rules; nothing builds an `allow`.
- A clone that is never re-rendered stays without the deny. The owner runs `wb rerender` once to get it.
- A rule that names a path the agent legitimately must write would block it. No agent-safe command writes the manifest.
- Whether to run a security review of the change is the owner's to ask.

## Review record

Empty until a review is asked for.

## Deferred work

- Corroborating the recorded hashes in the guarded store.
- The three Low findings of the security review of Increment B.

## Result

### Increment A — Protect the local manifest in the rendered permissions

**Done.** `harnessstage.stage` passes `protect=tuple(done.confined) + (localmanifest.PATH,)` to `render_permissions`, so every
rendered permissions file denies `Edit` on `.workbench/local/harness.json` in the three spellings, with or without the hook
(the argument is outside the `if hook or gate` block). Four tests were written first: two in `tests/test_hook_render.py`
(`Attached`: three spellings with the hook; denied without a hook, and no `exclude` rule) were red for the missing rule and are
green; two in `tests/test_rerender.py` (`Plan`: the rendered file denies the manifest; a live file without the rule makes the
preview list the permissions file as changed, with nothing kept or removed). The specs say it:
`command-permissions.md` (a bullet), `harness-refresh.md` ("Limits as built", the finding marked closed for the harness's tool
only) and `harness-modules.md` (one sentence; this file was not in the plan's list, and the sentence only corrects a statement
that the manifest deny would otherwise contradict).

**Verification as run.** `tests.test_hook_render` 43 OK; `tests.test_rerender.Plan` 21 OK; the full suite
`python3 -B -W error tests/run_all.py` 5910 tests in 12 roots OK (started before the two `test_rerender` tests were added; those
ran alone and passed, so the suite as it now stands was not run in one piece); `git diff --check` clean; `wb check` found no
problems. `wb run code-work check` ran when the plan was written (61 plans) and not again.

**Review.** One `reviewer` exchange, no blocking findings. It found nothing in production that needs the harness's write tool on
the manifest (every reference is installer code through `Writer`). Applied: the absolute spelling is now asserted in the rerender
test. Not applied: a second-preview assertion after a write (the unchanged-table case is covered by an existing test); a test of
criterion 2, which the code structure guarantees.

**Not done.** The scratch-clone run (attach, read the three denies, edit the manifest with the harness's tool and see it refused)
was not made; whether the harness's `Edit` deny also covers its other file-writing tools is not checked here. A clone gets the
rule at its next `wb rerender`; this clone has not been re-rendered. The plan's own `Status:` line still says `Proposed`.
