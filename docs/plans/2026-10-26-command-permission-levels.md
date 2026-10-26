# Command permission levels

Status: Approved
Created: 2026-10-26
Candidate: none (an owner request that implements the accepted decision `2026-10-26-per-command-permission-levels`; no roadmap candidate names it yet)
Specs: command-permissions, trust-and-approval, code-work, installer-interface, harness-modules, review-engine

## Goal

The owner can approve a plan and extend a review from a session with no terminal, by choosing the level of those two actions
in the personal settings, without weakening anything else. When the plan is done, the owner's table of levels exists and
is read safely, `approve-plan` and `wb run review-engine extend` can be set to `ask`, a harness renders what the table says,
every run at a level other than `block` is logged, and the specs say so.

## Scope

- The `levels` table in the personal settings, its keys, its offered levels and its shipped defaults, built as in
  `docs/specs/command-permissions.md`.
- `approve-plan` at `ask`, with its digest, and at `none`, with no digest and no preview; and `delegated` as it already
  works, now logged.
- `wb run review-engine extend` at `ask`, with a digest of the review's `status`, and at `none`, with no digest.
- Rendering of `ask` and no rule in a harness that provides `permissions`, and the check that reports a table that differs
  from the rendered rules.
- The append-only log.
- A trial that shows whether an interactive `ask` prompt reaches the owner's remote channel.
- The spec edits that follow once the decision is accepted.

## Non-goals

- The other keys of the decision's table: `reset`, `archive`, `prune`, `amend`, `acknowledge-second-tier`,
  `submit-remote-job`, `push-shared-branch`. Each needs its own preview digest defined in its spec, so each is its own plan.
  Until then they keep their present behavior, which is `block` (`stop`).
- Any trust-changing command (`install`, `adopt`, `add`, `upgrade`, `attach`, `approve`, `pin`). They stay `block` by
  default and offer only `block` in this plan. A key offers another level only from the version that builds it
  (`command-permissions.md`, "Which levels a key offers"), and each of these keys is for a later plan. The owner wants every
  command to offer every sensible level; this plan builds that for the two keys of F and G and for the table, the log and
  the rendering that the rest will use.
- Anything on the compiled floor, `safe-git commit` and `remove`, and push.
- A command that edits the table. The owner edits it by hand, as for checkpoints today.
- Accepting the decision. That is the owner's act and is not part of any increment.

## Assumptions and constraints

- The decision `2026-10-26-per-command-permission-levels` is `Accepted` before Increment A starts. If the owner changes
  it, this plan is revised first and re-approved. The spec `command-permissions.md` is `Draft` and is edited here.
- Discovery tooling: skipped, because no discovery tooling is installed. The impact was read from `workbench/settings.py`
  (the table and `effective`), `workbench/rules.py` (`OWNER_RUN`, `AGENT_SAFE`, `command_owner_patterns`),
  `workbench/harnessplan.py` and `workbench/harnessstage.py` (rendering), `workbench/commands.py` (`owner_refusal`),
  `workbench/planapprovals.py` and `workbench/delegation.py` (plan approval), `workbench/settingscmd.py`,
  `docs/development.md` and the specs named above, on 2026-10-26 at `36c0970`. The module code of `review-engine` was not read
  yet; Increment G begins with reading it, and the plan is revised if it disagrees.
- The workbench is standard library only (`2026-10-19-implementation-language`). A module's code lives in the module
  (`2026-10-21-module-code-lives-in-modules`), so the `extend` digest is built in `review-engine`, not in the installer.
- Rendered rules change only at an attach, which is owner-run. Changing the table is therefore a terminal act, rarely done;
  what the owner does day to day remotely is answer the prompt.
- The terminal test is a mistake guard (`2026-10-20-preview-then-owner-run-write`). An `ask` is the harness's prompt, whose
  behavior in an interactive session is unverified (Increment A).
- Every increment is one verified, reviewed local commit made through the project's commit helper, and the commit message
  carries the trailer `Plan: 2026-10-26-command-permission-levels#<label>`.

## Completion criteria

1. `command-permissions.md` is `Current`, matches the code, and the edits to the other specs listed in Increment H exist.
2. With no settings or a version 1 file, no action that an agent cannot run today becomes runnable, and `wb settings`
   prints the same checkpoint lines as before; a test shows this.
3. At `ask`, `wb approve-plan <plan> --digest <12>` and `wb run review-engine extend <document> <n> --digest <12>` run without a
   terminal only when the digest matches, the rendered `ask` rule is present and the log entry is written; each is refused
   otherwise, with nothing written. At `none` each runs without a terminal and without a digest only when the rendering
   record shows no rule for it and the log entry is written, and is refused otherwise. A delegated plan approval writes its
   log entry first and is refused when it cannot.
4. At `block` both still refuse without a terminal.
5. A table entry cannot name a floor action, cannot set a level a key does not offer, and a damaged table reads as `block`.
6. The trial of Increment A is recorded with its result, and the plan was stopped and revised if it failed.
7. The full test suite passes, `wb check` and the document checks report nothing new, and nothing outside the increments'
   affected areas changed.

## Increments

### Increment A — Trial: can an `ask` prompt be answered remotely

**Outcome:** the spec's unverified assumption is settled with evidence, and the plan continues or stops on it.
**Dependencies:** the decision is Accepted; this plan is Approved.
**Affected areas:** `docs/specs/harness-modules.md` (an evidence note only) and this plan's Result. No code.
**Steps:**
1. Owner step, in a terminal: attach the Claude harness in a throwaway project with one harmless command rendered as an
   `ask` (the existing `harness-modules.md` trial project is the model). The agent describes the steps and runs none of them.
2. Owner step, from the remote channel with no terminal: start an interactive session in it, have the agent run the command,
   and answer the prompt. Then answer it a second time with a refusal.
3. Record: the tool versions, the commit, whether the prompt reached the remote channel, whether answering ran or refused
   the command, and whether the owner's global `PermissionRequest` hook fired.
4. Write the evidence note in `harness-modules.md` and the Result of this plan.
**Verification:** the note states what was run and what was observed, and no step is claimed that was not run.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-command-permission-levels#A`. **Stop condition:** if
the prompt cannot be answered remotely, stop and report; `ask` is then not offered by this design and the plan is revised.

### Increment B — The levels table in the settings reader

**Outcome:** the personal settings accept `version` 2 with `levels`, and every key reads as it does today.
**Dependencies:** A.
**Affected areas:** `workbench/settings.py`, `workbench/settingscmd.py`, `tests/test_settings*.py`.
**Steps:**
1. Write the tests first: a version 1 file and no file read exactly as now; `levels` with each level; an unknown value, a
   non-string, a duplicate key, a damaged file and an unsupported version read as `block` with a note; `stop` and `delegate`
   in `checkpoints` read as `block` and `delegated`; a key in both takes the stricter.
2. Extend `load` and `effective` to build the table with the strictness order. Keep `delegate` effective for `approve-plan`
   only, as now, and keep every other `delegated` reading as `block` until C declares a gate.
3. `wb settings` prints `level <key>: <level>` and keeps the `checkpoint` lines.
**Verification:** `python3 -m unittest discover -s tests -p 'test_settings*.py'`, then `python3 -B -W error tests/run_all.py`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-command-permission-levels#B`.

### Increment C — Keys, offered levels and shipped defaults

**Outcome:** a registry says which keys exist, which levels each offers and its default, and the reader uses it.
**Dependencies:** B.
**Affected areas:** a new `workbench/levels.py`, `workbench/settings.py`, `workbench/rules.py` (a test that every
`OWNER_RUN` command and every declared checkpoint has a registry entry), `tests/test_levels.py`.
**Steps:**
1. Write the tests first: an unknown key and a floor key are refused; `delegated` is offered only to `approve-plan`;
   `accept-decision` offers `block` only in this plan, because no agent-run acceptance command or preview exists and its
   `ask` is for a later plan; no key offers `ask` until Increment F or G enables it; the default of
   every key is `block` in this increment.
2. Build the registry from `rules.OWNER_RUN`, the process module's checkpoints and a module's declared owner arguments,
   with the floor excluded by id. A test fails when a new owner-run command has no entry, as `rules.py` already does for
   routing.
3. Apply the registry in the reader.
**Verification:** the new and settings tests, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-command-permission-levels#C`.

### Increment D — The log

**Outcome:** a run at a level other than `block` writes an entry first, and does nothing when it cannot.
**Dependencies:** C, and the owner's recorded answer at the security checkpoint (step 1).
**Affected areas:** a new `workbench/levellog.py`, `workbench/store.py` only if a new store file kind is needed,
`workbench/delegation.py` (the delegated approval writes its entry first), `tests/test_levellog.py`, the delegation tests.
**Steps:**
1. **Security checkpoint (owner).** This is the first increment that writes the guarded store, and the work changes who may
   approve a plan and extend a review. Stop and ask the owner whether to run a security review of the design now, and record
   the answer, the reviewer and the outcome in the Result. A review runs only when the owner asks. Ask again before H, on
   the built code. An answer of no is recorded and the increment continues.
2. Write the tests first: an attempt line and an outcome line share an operation identifier and neither is rewritten; each
   line is within 1,024 bytes; a damaged log is reported and refuses the action; the agent's harness deny covers the file; a
   `block` run writes nothing; `delegate-approve-plan` writes its attempt before the approval and refuses, writing no
   approval, when it cannot; a refusal after the attempt, and a success, each write an outcome; an attempt with no outcome
   is listed as unfinished; an outcome that cannot be written after the action is reported and exits non-zero.
3. Build the two-line append (attempt before, outcome after on every path), a reader for the owner, and call it from
   `delegation.py`. Increments F and G call it for `ask` and `none`, and test the same two lines for both.
**Verification:** the new tests, the harness deny test, the delegation tests, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-command-permission-levels#D`.

### Increment E — Rendering and the drift check

**Outcome:** an attached harness holds a `deny`, an `ask` or no rule for an owner-run key as its level says, attach records
what it rendered in the guarded store, and `wb check` reports a harness file that differs from the record. An effective
level is `block` unless the record shows the rule.
**Dependencies:** D.
**Affected areas:** `workbench/rules.py`, `workbench/harnessplan.py`, `workbench/harnessstage.py`, `workbench/attach.py` (it
writes the rendering record), `workbench/store.py`, `workbench/check.py`, the
Claude module's rendering, tests under `tests/` and `packages/workbench/claude/tests/`.
**Steps:**
1. Write the tests first, with a synthetic harness: a key at `block` renders its `deny`; at `ask` an `ask` and no `deny`; at
   `none` neither; the guarded-store deny and the floor's `ask` rules are unchanged whatever the table says; with no
   `permissions` capability the key reads as `block`; with no rendering record, a damaged record, a table changed since
   attach or an unattached harness every key reads as `block`.
2. Render from the table at attach, and write the rendering record in the guarded store (the harness's identity, whether it
   provides `permissions`, a digest of the effective table, and the rule rendered per key), as `command-permissions.md`,
   "Rendering", specifies. A neutral rule list still holds only `ask` and `deny`.
3. Add the drift check, which compares the harness file with the record, and a function that answers a key's effective
   level from the record to the commands, which read it in F and G.
**Verification:** the new tests, `python3 -B -W error tests/run_all.py`, and `python3 -m workbench check` on this repository.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-command-permission-levels#E`.

### Increment F — `approve-plan` at `ask` and `none`

**Outcome:** the owner can approve a plan from a prompt, bound to the plan's region digest.
**Dependencies:** E.
**Affected areas:** `workbench/planapprovals.py`, `workbench/cli.py` (the argument grammar), the read-only preview that prints
the digest (`plan-status` or a sibling), `workbench/levels.py` (offer `ask` and `none` for the key), tests.
**Steps:**
1. Write the tests first: at `ask`, the command with a matching digest approves and writes the same record as the owner's
   terminal command; a mismatch, a plan edited after the preview, a missing rendered rule, an unwritable log and a missing
   digest each refuse and write no approval; at `block` it still refuses without a terminal; the terminal path is unchanged; at `none` it runs with no digest only when
   the record shows no rule and the log is written, and a digest given at `none` is refused as an unknown argument.
2. Print the digest in the read-only preview, and have the command recompute it in its own process.
3. Write the log entry before the approval, and the approval from the bytes already held.
4. Change the registry default of `approve-plan` to `ask`, and test that with no settings or a version 1 file it reads `ask`
   only when the rendering record shows the `ask` rule after an attach, and `block` otherwise.
**Verification:** the new tests, the plan-approval and delegation tests, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-command-permission-levels#F`.

### Increment G — `wb run review-engine extend` at `ask` and `none`

**Outcome:** the owner can extend a review that reached its bound from a prompt, bound to the review's state.
**Dependencies:** F.
**Affected areas:** `commands.owner_refusal`, the `review-engine` module's helper, its declaration and tests.
**Steps:**
1. Read the module's code and `docs/specs/review-engine.md`; if it disagrees with this plan, stop and revise the plan.
2. Write the tests first: a matching digest of the `status` extends within the ceiling; a changed review, a missing rendered
   rule and an unwritable log refuse; the ceiling of 5 still holds at every level; at `block` the terminal test is unchanged; at `none` it extends with no digest
   only when the record shows no rule and the log is written, still within the ceiling.
3. Keep the grammar `extend <document> <n>` (`n` from 1 to 5, as `review-engine.md` defines) and add `--digest <12>` at
   `ask`. The digest covers the review's `status` and `n`, so a different increase is not approved by an earlier answer.
   Make `owner_refusal` read the effective level, and let `extend` print and require the digest.
4. Change the registry default of `wb run review-engine extend` to `ask`, with the same no-settings and version 1 test as
   in F.
**Verification:** the module's tests, the `commands` tests, then the full suite.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-command-permission-levels#G`.

### Increment H — Specs and documentation

**Outcome:** the specs say what is built.
**Dependencies:** G, and the owner's recorded answer to the second security question, asked before this increment on the
built code (the decision is already Accepted).
**Affected areas:** `docs/specs/command-permissions.md` (`Current`), `trust-and-approval.md`, `code-work.md` (the checkpoint
table, and `accept-decision` no longer listed as delegable), `installer-interface.md` (the `approve-plan` grammar and
`wb settings`), `harness-modules.md`, `review-engine.md`, `docs/specs/README.md`, `docs/development.md`.
**Steps:**
1. Edit each spec in place to match the code, and record in `command-permissions.md` which keys are built.
2. Update the command table in `development.md` for `approve-plan`, `extend` and `settings`.
3. Ask the owner to run the document checks. (The status line of `2026-10-23-delegated-plan-approval` was changed on
   2026-10-26 at the owner's request, in the commit that recorded the decision; nothing more is edited there.)
**Verification:** the owner runs the document checks; a search for the old wording finds none in a living document.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-command-permission-levels#H`.

## Verification for the plan as a whole

`python3 -B -W error tests/run_all.py`; `python3 -m workbench check`; the plan check
(`python3 -m workbench run code-work check`); `git diff --check`; and the owner's document checks. The trial of A is
repeated against the finished code in a throwaway project: approve a plan and extend a review from the remote channel, and
see each refuse with a wrong digest.

## Risks and sensitive actions

- **Authorization and the guarded store.** The work changes who can approve a plan and extend a review, and adds a file to
  the guarded store. The owner decides whether to run a security review. The plan stops to ask at Increment D, step 1,
  and again before H, records each answer in the Result, and runs no review itself.
- **`ask` approves a command and a digest.** A hurried answer becomes an approval. The residual risk is accepted in the
  decision, and the preview must be shown in the conversation first.
- **The prompt may not work remotely.** If A fails, the plan stops.
- **A table that loosens a default.** The shipped defaults stay `block` in B to E, and `ask` ships only for the two keys
  of F and G.
- **A stale rendered rule.** The table and the rendered rules can differ until the next attach. E makes the key read as
  `block` and `wb check` reports it.
- **Owner steps.** Increment A needs the owner's terminal and remote channel; H needs the owner to run the document checks.
- **Hard stops.** None of the increments touches the compiled floor or a hard stop.

## Review record

Reviewed by the review engine through the `ask-codex` bridge (model `gpt-5.6-terra`, effort medium) on 2026-10-26, at
the owner's request: three rounds, the bound of 3, not extended. Outcome: not converged. Round 1 found that the plan
implied a digest at `none` (R1-F1), left the delegated approval out of the log (R1-F2) and had no security-review
checkpoint (R1-F3). Round 2 found that `extend` had lost its increase argument (R2-F1), that no step moved the two
shipped defaults to `ask` (R2-F2), that the plan and spec disagreed about `none` for deferred keys (R2-F3) and that a step
was stale (R2-F4). Round 3 found that an append-only log written before the action cannot hold an outcome (R3-F1) and that
`accept-decision` was given an `ask` that nothing can serve (R3-F2). All nine were applied. R2-F4 was applied by removing
a stale step, and its claim that the status-line change breaks policy was not accepted; that stays with the owner. The
text added for R3-F1 and R3-F2, and the spec edits made for R2-F3 and R3-F1, were not reviewed again. The owner approved
the plan on 2026-10-26 with `wb approve-plan`, knowing that the review did not converge and that those edits were not
reviewed again.

## Deferred work

- The other keys of the decision's table, each with its own preview digest, in later plans.
- A command that edits the table, if hand edits prove error-prone.
- A roadmap candidate for this work, if the owner wants one.
- Removal of the `checkpoint` lines of `wb settings` and the `stop` and `delegate` words, once nothing reads them.

## Result

Empty until work starts.
