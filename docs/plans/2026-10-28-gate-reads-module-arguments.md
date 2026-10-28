# Let the command gate read a module argument as data

Status: Proposed
Created: 2026-10-28
Candidate: none (an owner request that follows a gap found in use and recorded in the Result of `2026-10-27-levels-for-the-review-workflow`; no roadmap candidate names it)
Specs: command-permissions.md, review-engine.md

## Goal

An agent can run the read-only previews of the review engine (`preview extend`, `preview reset`, `preview archive`,
`preview amend`, `preview prune`) while the owner has set the matching key to `ask` or `none`, so that the owner can see what a
digest binds from a phone. Today the command gate refuses them. When the plan is done, a call that dispatches to a different
argument of the same module command, with literal arguments, is not taken for the relaxed argument, and every call that does
dispatch to the relaxed argument is judged as it is now.

## Scope

- The command gate (`workbench/command_gate.py`, `judge`) for a key of the form `wb run <command> <argument>`: a command that is
  exactly one literal `wb run <command> <first> ...`, where `<first>` is a plain token other than `<argument>`, is not searched
  for the key's words. This is the rule the accepted decision `2026-10-27-command-gate-literal-arguments` gave to single-word keys
  (`wb install`), carried to the keys it left out.
- A new decision record that says so (the accepted one names these keys as not exempted and is not edited).
- Tests of the gate, and the spec text.

## Non-goals

- No change to the levels, the rendering, the log, the launcher, the helper, the digests or any module.
- No change to how a single-word key, `approve-plan`, a quoted, compound or substituted command, or a `wb launch` spelling is
  judged.
- No exemption by a module's name: only the module command of the key (`<command>` equal to the key's), so a differently named
  pin of the same helper is not freed.
- No tokenizer or shell parser; the gate stays a text match and a speed bump, not a barrier.
- Not the two older specs that still say `wb run` always needs a terminal (see Deferred work).

## Assumptions and constraints

- The finding: with the five review-engine keys at `ask`, an agent's `wb run review-engine preview extend <document> <n>` was
  refused by the gate on 2026-10-28 (commit `c1917f8`), because the text holds `review-engine` and then `extend`, and it is not
  the simple form the `ask` rule matches. The same holds for the other four previews, and also for any call that merely holds
  the two words in order, such as a `decide` whose reason says `extend`.
- The launcher dispatches on the first argument only: it refuses a first argument that the declaration does not list
  (`commands.py`, around line 99) and tests the owner-run list on that same first argument (`owner_refusal`, around line 239). A
  call whose first argument is `preview` therefore never runs `extend`; the helper's `preview extend` is read-only.
- A first argument written in quotes, or with a quote inside it, is not a plain token: bash would remove the quotes, so the gate
  must not read `'extend'` as another argument. The rule requires a plain first token.
- `workbench/` core is directly editable, but the gate is live and imports `workbench/`. The change is made and tested in a scratch
  copy, and the real file is edited once, so the gate is never half-edited.
- Accepting the decision is the owner's act. No security review runs unless the owner asks; the decision it relies on says one is
  owed when the gate is built.
- Nothing tracked points to anything untracked; no secret appears in the plan or the tests (fixtures that look like one are built
  at run time).

## Completion criteria

1. A decision record `Proposed` by Increment A has been accepted by the owner before Increment B begins.
2. With `wb run review-engine extend: ask` (and each of the other four, and at `none`), `judge` allows
   `wb run review-engine preview <argument> <document> ...` and still blocks `wb run review-engine 'extend' ...`, a compound command,
   a double-quoted or substituted first argument, and a differently named command that holds the two words; it still allows the
   exact simple form of the relaxed command itself.
3. `command-permissions.md` and `review-engine.md` state the rule and its limits; the known gap in the earlier plan's Result is
   closed by a Result entry here.
4. The full test suite, `doccheck`, `refcheck`, `wb run code-work check`, `wb check` and `git diff --check` pass.

## Increments

### Increment A — Decide that a module argument is read as data

**Outcome:** a decision record `docs/decisions/2026-10-28-gate-reads-module-arguments.md`, `Proposed`, that refines
`2026-10-27-command-gate-literal-arguments`: for a key `wb run <command> <argument>`, a literal `wb run <command> <first> ...` whose
plain first token is not `<argument>` does not name the key. It states the alternatives (leave the gap and tell the owner to run
previews; rename the preview, which fails because the gate reads the skeleton; exempt any module name, which frees a renamed pin;
read the declaration in the gate; a shell parser), the consequences (a `decide` reason or a path holding the words stops being
blocked; the quoted-first-token and compound cases stay blocked) and the evidence. It is indexed in `docs/decisions/README.md`.
**Dependencies:** none.
**Affected areas:** `docs/decisions/2026-10-28-gate-reads-module-arguments.md` (new), `docs/decisions/README.md`.
**Steps:**
1. Read `docs/decisions/README.md` and the accepted decision it refines; run `judge` from a scratch copy on the refused command
   and on the cases in Increment B to record what the gate does today.
2. Draft the record from the template, status `Proposed`, with a provenance line (what was run, versions, commit).
3. Add its row to the index as `Proposed`.
4. Stop and tell the owner that it waits for them. Do not start Increment B until the owner has accepted it.
**Verification:** `doccheck`, `refcheck`, `git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-28-gate-reads-module-arguments#A`. The record stays `Proposed`
until the owner accepts it by their own act.

### Increment B — The gate reads the first argument

**Outcome:** `judge` does not search a literal `wb run <command> <first> ...` for the words of a key `wb run <command> <argument>`
when the command name equals the key's and `<first>` is a plain token other than `<argument>`. Every other form is judged as now.
**Dependencies:** A, accepted by the owner.
**Affected areas:** `workbench/command_gate.py`, `tests/test_command_gate.py`.
**Steps:**
1. Write the tests first and see them fail for the right reason (cases below), in the existing style of `tests/test_command_gate.py`.
2. Add a helper beside `literal_run` that returns the name and the first argument of a literal call, and use it in `judge` where
   `literal and _by_launcher(key)` already skips the search. Edit the definition before its caller and keep `workbench/` importable
   between edits; make the change in a scratch copy, run the tests there, then edit the real file once.
3. Update the module docstring bullets to describe the new case.
**Cases:** with each of the five keys at `ask` and at `none` — allowed: `preview <key's argument> <document> <n>`; `decide <document>
<finding> applied --reason 'extend the bound'`; `status <document>`; the exact simple form of the relaxed command, with and without
`--digest <32 hex>`. Blocked: `'extend' <document> <n>`; `ext''end <document> <n>`; `"preview" extend ...`; `preview extend <document> 4;
wb run review-engine extend <document> 4`; `A=preview; wb run review-engine $A extend ...`; `wb run review-engine $'\x65xtend' ...`; a
differently named command, `wb run other preview extend`, which is judged as now; `wb run review-engine` followed by a newline
outside quotes; a trailing newline. Unchanged: the single-word keys, `approve-plan` and `wb run mempalace init`.
**Verification:** `tests/test_command_gate.py` from a scratch copy (`cd <scratch> && env PYTHONPATH=. python3 -B -W error -m unittest
tests.test_command_gate`), then the full suite in the background in that copy, then in the real tree `wb check`, `wb run code-work
check` and `git diff --check`. A `reviewer` review is mandatory. Ask the owner whether to run a security review of the gate change
before the commit; run it only if they say yes.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-28-gate-reads-module-arguments#B`.

### Increment C — Specs

**Outcome:** the text states the rule. `command-permissions.md` ("The command gate", the "Limits" bullet on a command that merely
names the word, and the review-engine map rows' "What can block" for the previews) says that a preview of the review engine is
allowed at `ask` and `none`, and what is still blocked; `review-engine.md` says an agent can run the preview at any level, and
that the prompt still shows the digest and not the preview, so the agent shows it first.
**Dependencies:** B.
**Affected areas:** `docs/specs/command-permissions.md`, `docs/specs/review-engine.md`, `docs/decisions/README.md` (only if the
owner has accepted the record and the status line changes).
**Steps:**
1. Compare each changed sentence with the code and with `judge`.
2. Update the specs; remove nothing that is still true.
3. Run the document checks.
**Verification:** `doccheck`, `refcheck`, `wb run code-work check`, `git diff --check`; a `reviewer` review.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-28-gate-reads-module-arguments#C`.

## Verification for the plan as a whole

`python3 -B -W error tests/run_all.py` from a scratch copy (about 12 minutes, in the background), `wb check`, `wb run code-work
check`, `doccheck`, `refcheck` and `git diff --check`. No package changes, so no landing and no `release-approvals`. Then a trial with
the owner: with `extend` at `ask`, the agent runs `preview extend` on a plan and then the `extend` with the digest, and the harness
prompt appears.

## Risks and sensitive actions

- **A permission boundary.** The change loosens a gate that exists to stop a relaxed owner-run command from being run by an agent.
  The gate is a speed bump and not a barrier (`command-permissions.md`, "Limits"); the rule is safe only because the launcher
  dispatches on the first argument and refuses undeclared ones, and because the first token must be plain and the whole command a
  single literal call. If a module's helper ran another of its arguments from the text of its own arguments, the gate would not
  see it; that is the module's pinned code, which the owner approved.
- **Untrusted text.** The gate parses text an agent writes. A first token spelled with a quote, an escape, an expansion or a glob is
  not plain, so it stays blocked; the tests include each.
- **A live hook.** An error in `command_gate.py` blocks or frees every Bash call. The change is built and tested in a scratch copy
  and landed with one edit; if the gate fails, it blocks (`gate_hook.guard`).
- **Security review.** The earlier decision says one is owed when the gate is built. It runs only when the owner asks, and the
  owner is asked before the Increment B commit.
- **No irreversible or external action.** Nothing is pushed; commits are local and the owner's word.

## Review record

Empty until a review is asked for.

## Deferred work

- `docs/specs/module-boundary.md` and `docs/specs/trust-and-approval.md` still say `wb run` runs an owner-run argument only when
  both streams are terminals, which is false for the review engine at `ask` or `none` (found in Increment G of
  `2026-10-27-levels-for-the-review-workflow`). Neither is in this plan's specs; a small separate change.
- A call that holds the words in a different command (`wb run safe-git commit --subject 'extend review-engine'`) stays blocked
  while a key is relaxed, because the rule frees only the key's own command. Freeing it needs a decision about renamed pins.
- The `wb launch` spelling stays terminal-only for an owner-run argument.

## Result

### Increment A — drafted, waiting for the owner (2026-10-28)

- Wrote `docs/decisions/2026-10-28-gate-reads-module-arguments.md` as `Proposed` and added its row to `docs/decisions/README.md`.
  It refines `2026-10-27-command-gate-literal-arguments` without editing it.
- Probe: `judge` at commit `49cbf62` (Python 3.15.0) with `wb run review-engine extend` and `... reset` relaxed. Today it blocks
  `preview extend` (key `extend`) and `preview reset` (key `reset`), blocks a `decide` whose reason says `extend`, and allows
  `status`, the exact simple forms and `wb run other preview extend`. Every quoted, compound, substituted and newline spelling is
  blocked. The proposed rule was not built or tested.
- Verification: `doccheck`, `refcheck` and `git diff --check` clean.
- Review: one `reviewer` exchange, no blocking finding. Applied: the "same limit on the characters" wording (there is no per-token
  limit, only the 64 KiB cap), the `wb run --provides` case, the per-key consequence, and that the helper's read-only `preview` is
  known by reading. Not applied: a re-runnable probe (Increment B's tests are the durable record).
- Not done: the record is not accepted. Increment B cannot start until the owner accepts it.
