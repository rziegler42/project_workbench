# Command permission levels

Status: Proposed
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
- A trial that shows whether an interactive `ask` prompt reaches the owner's remote channel (done, Increment A).
- The changes the design-stage security review asked for (Revision 1 below): an appended, bounded log; a rendering record
  that lists every key and the harness file's hash; a 32-character digest that covers the declaration, helper and project;
  a bad key that blocks the whole table; a refused duplicate key; and the `ask` pattern for the store's `bin/wb` path.
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
- **Revision 1 (2026-10-26), after the security checkpoint of Increment D.** The owner answered yes and the
  `security-reviewer` agent read the design (read-only in effect; its scratch write was refused, so nothing it reports is
  tested). The findings are recorded in the Result and are folded into D, E, F and G below. The one finding that is a
  decision and not a fix is HIGH-1: at `ask` and `none` the only barrier is a harness rule that matches command text, which a
  path-qualified `wb` or a shell edit of the harness file can walk around. The mitigations here are the live-file hash check
  and the `bin/wb` pattern; the residue is accepted by the owner in a decision (`Proposed` by the agent, accepted by the
  owner) before `ask` ships for any key. Increment F depends on that decision being `Accepted`.
- Every increment is one verified, reviewed local commit made through the project's commit helper, and the commit message
  carries the trailer `Plan: 2026-10-26-command-permission-levels#<label>`.

## Completion criteria

1. `command-permissions.md` is `Current`, matches the code, and the edits to the other specs listed in Increment H exist.
2. With no settings or a version 1 file, no action that an agent cannot run today becomes runnable, and `wb settings`
   prints the same checkpoint lines as before; a test shows this.
3. At `ask`, `wb approve-plan <plan> --digest <32>` and `wb run review-engine extend <document> <n> --digest <32>` run without a
   terminal only when the digest matches, the rendered `ask` rule is present and the log entry is written; each is refused
   otherwise, with nothing written. At `none` each runs without a terminal and without a digest only when the rendering
   record shows no rule for it and the log entry is written, and is refused otherwise. A delegated plan approval writes its
   log entry first and is refused when it cannot. At `ask` and `none` the harness file must also hash to the rendering
   record's hash.
4. At `block` both still refuse without a terminal.
5. The log is appended and never rewritten, holds at most 4 MiB, and a full log refuses runs above `block` with a message that
   names it. The rendering record lists every key and a key it does not list reads as `block`. A key that is not a valid name
   blocks the whole table. The registry refuses two declarations of one key.
6. A table entry cannot name a floor action, cannot set a level a key does not offer, and a damaged table reads as `block`.
7. The trial of Increment A is recorded with its result, and the plan was stopped and revised if it failed.
8. The decision `2026-10-26-ask-level-spelling-limit` is recorded in the Result as accepted by the owner before `ask` shipped
   for any key, and the spelling probe of Increment F is recorded with its result.
9. The full test suite passes, `wb check` and the document checks report nothing new, and nothing outside the increments'
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

**Outcome:** a run at a level other than `block` writes an entry first, and does nothing when it cannot; the log is appended,
bounded and cannot be filled by an agent without limit; and two carry-over fixes to the reader and the registry are made.
**Dependencies:** C. Step 1 is done (Revision 1): the owner answered yes and the review's outcome is in the Result.
**Affected areas:** `workbench/wbkit/safefs.py` (a new append call; check whether the kit is mirrored under `packages/` and
keep the copies identical), a new `workbench/levellog.py`, `workbench/store.py` only if a new store file kind is needed,
`workbench/delegation.py` (the delegated approval writes its entry first), `workbench/settings.py` and `workbench/levels.py`
(the carry-over fixes, with `tests/test_levels.py` and `tests/test_settingscmd.py`), `tests/test_levellog.py`, the delegation, settings and levels tests.
**Steps:**
1. **Security checkpoint (owner): done.** Asked on 2026-10-26; the answer was yes; the findings are in the Result. Ask
   again before H, on the built code, and again after F with a probe of the spelling bypass on a copy (see F).
2. Write the tests first, and see them fail: two appends run in parallel keep both lines; a symbolic link, a FIFO, a
   directory and a file with more than one link at the log path are refused; a damaged log is reported and does not stop the
   reader; the log at 4 MiB refuses a run above `block` with a message that names it; each line is within 1,024 bytes counted
   in bytes, with a reason cleaned of control characters and then cut to 200 characters; the operation identifier comes from
   `secrets`; an attempt line and an outcome line share an identifier and neither is rewritten; the agent's harness deny
   covers the file; a `block` run writes nothing; a run that changes nothing (an approval that already exists) writes
   nothing; the attempt is written after every read-only check and immediately before the change of state, so a refusal
   before it leaves no entry; `delegate-approve-plan` writes its attempt before the approval and refuses, writing no
   approval, when it cannot; a refusal after the attempt, and a success, each write an outcome; an attempt with no outcome
   is listed as unfinished and the reader says that this does not mean "not approved"; an outcome that cannot be written
   after the action is reported and exits non-zero; a bad key in `levels` blocks the whole table; a registry with two
   declarations of the same key is refused.
3. Add the append call to `safefs` (`O_APPEND`, `O_NOFOLLOW`, regular file, one link, one write of one line, fsync, no read
   of the existing file). Build the two-line append, a reader for the owner that cleans what it prints and parses by field
   position with the reason last, and call it from `delegation.py`. Increments F and G call it for `ask` and `none`, and
   test the same two lines for both.
4. Make the carry-over fixes: `settings.load` sets `levels_blocked` when any key in `levels` is not a valid name;
   `levels.registry` refuses two declarations that give one key; and `levels.registry` no longer makes `wb acknowledge` a
   key, because that command already reaches the checkpoints `acknowledge-first-tier` and `acknowledge-second-tier` and the
   spec gives a checkpointed action its checkpoint's name as its key (review finding R1-F1 of this revision; Increment C
   added the extra key). Tests: the pinned `OWNER_RUN_KEYS` list, `wb settings` and the registry tests change accordingly,
   and a test shows that a command with a declared checkpoint has no command-spelling key.
**Verification:** the new tests, the harness deny test, the delegation, settings and levels tests, then the full suite.
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
   provides `permissions`, a digest of the effective table, a hash of the harness file written, and the rule rendered for
   every key with `none` written and not implied), as `command-permissions.md`, "Rendering", specifies. A neutral rule list
   still holds only `ask` and `deny`. For an `ask` key attach also renders the pattern for the store's own `bin/wb` path.
   Tests added first: a record with one key deleted reads that key as `block`; a harness file edited after attach makes
   `ask` and `none` read as `block`; the `bin/wb` pattern is rendered.
3. Add the drift check, which compares the harness file with the record, and a function that answers a key's effective
   level from the record to the commands, which read it in F and G; it refuses `ask` and `none` when the harness file no longer hashes to the record.
**Verification:** the new tests, `python3 -B -W error tests/run_all.py`, and `python3 -m workbench check` on this repository.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-command-permission-levels#E`.

### Increment F — `approve-plan` at `ask` and `none`

**Outcome:** the owner can approve a plan from a prompt, bound to the plan's region digest.
**Dependencies:** E, and the decision `docs/decisions/2026-10-26-ask-level-spelling-limit.md` accepting the HIGH-1 residual
risk (step 0). If it is not `Accepted`, stop: `approve-plan` does not ship at `ask`.
**Affected areas:** `workbench/planapprovals.py`, `workbench/cli.py` (the argument grammar), the read-only preview that prints
the digest (`plan-status` or a sibling), `workbench/levels.py` (offer `ask` and `none` for the key), tests.
**Steps:**
0. **Owner checkpoint.** Before any code, draft the decision `docs/decisions/2026-10-26-ask-level-spelling-limit.md` as
   `Proposed` with the `draft-decision` skill (the problem: at `ask` and `none` the only barrier is a harness rule that
   matches command text; the mitigations: the live-file hash check and the `bin/wb` pattern; the residue: other spellings;
   the alternative: hold `ask`), then stop and ask the owner. Record in the Result whether the owner accepted it and when.
   Only the owner accepts a decision. If it is not accepted, stop and revise the plan.
1. Write the tests first (the digest is 32 hexadecimal characters of the canonical preview, which holds the project
   identifier, the declaration hash and the helper hash): at `ask`, the command with a matching digest approves and writes the same record as the owner's
   terminal command; a mismatch, a plan edited after the preview, a missing rendered rule, an unwritable log and a missing
   digest each refuse and write no approval; at `block` it still refuses without a terminal; the terminal path is unchanged; at `none` it runs with no digest only when
   the record shows no rule and the log is written, and a digest given at `none` is refused as an unknown argument.
2. Print the digest in the read-only preview, and have the command recompute it in its own process.
3. Write the log entry before the approval, and the approval from the bytes already held.
4. Change the registry default of `approve-plan` to `ask`, and test that with no settings or a version 1 file it reads `ask`
   only when the rendering record shows the `ask` rule after an attach, and `block` otherwise.
5. **Spelling probe, on a copy.** In a throwaway project with the harness attached by the finished code and `approve-plan` at
   `ask`, try each spelling an agent could submit that the rendered rules do not name: a path-qualified `wb`, the store's own
   `bin/wb`, `python3 -I -m workbench`, `bash -c` and `env wb`. Record, with tool versions and the commit, which spellings the
   harness stopped, which it let run, and which of those ran the approval. Owner steps are described and not run by the agent.
   **Stop condition:** if a spelling the pattern does not cover approves a plan without a prompt, stop, report, and revise the
   plan; `ask` does not ship for `approve-plan` until the owner decides.
**Verification:** the new tests, the plan-approval and delegation tests, then the full suite; the probe's record is in the
Result.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-command-permission-levels#F`.

### Increment G — `wb run review-engine extend` at `ask` and `none`

**Outcome:** the owner can extend a review that reached its bound from a prompt, bound to the review's state.
**Dependencies:** F (and so the accepted decision on the HIGH-1 residual risk).
**Affected areas:** `commands.owner_refusal`, `workbench/levels.py` (the offered levels and the default of the key), the
`review-engine` module's helper, its declaration and tests.
**Steps:**
1. Read the module's code and `docs/specs/review-engine.md`; if it disagrees with this plan, stop and revise the plan.
2. Write the tests first: a matching digest of the `status` extends within the ceiling; a changed review, a missing rendered
   rule and an unwritable log refuse; the ceiling of 5 still holds at every level; at `block` the terminal test is unchanged; at `none` it extends with no digest
   only when the record shows no rule and the log is written, still within the ceiling.
3. Keep the grammar `extend <document> <n>` (`n` from 1 to 5, as `review-engine.md` defines) and add `--digest <32>` at
   `ask`. The digest covers the review's `status` and `n`, so a different increase is not approved by an earlier answer.
   Make `owner_refusal` read the effective level, and let `extend` print and require the digest.
4. Enable `ask` and `none` for the key `wb run review-engine extend` in the registry, and change its default to `ask`, with
   the same no-settings and version 1 tests as in F and a test for an explicit `none`. The installer's tests forbid naming a
   module's command (`tests/test_boundary.py`), so the offer must come from the module's own declaration of the owner-run
   argument and not from a name in `levels.py`. If the declaration schema has no field for it, stop and revise the plan:
   adding one is a change to the declaration contract that this plan does not authorize.
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
see each refuse with a wrong digest; and the spelling probe of Increment F (it is part of F, not repeated here).

## Risks and sensitive actions

- **Authorization and the guarded store.** The work changes who can approve a plan and extend a review, and adds a file to
  the guarded store. The owner decides whether to run a security review. The plan stops to ask at Increment D, step 1,
  and again before H, records each answer in the Result, and runs no review itself.
- **`ask` approves a command and a digest.** A hurried answer becomes an approval. The residual risk is accepted in the
  decision, and the preview must be shown in the conversation first.
- **The prompt may not work remotely.** If A fails, the plan stops.
- **A table that loosens a default.** The shipped defaults stay `block` in B to E, and `ask` ships only for the two keys
  of F and G.
- **`ask` is bypassable by spelling (HIGH-1).** The mitigations are the live-file hash check and the `bin/wb` pattern. The
  rest is a stated limit that the owner accepts in a decision before F. After F a probe of the spelling bypass is run on a
  copy and recorded; if it succeeds with a spelling the pattern does not cover, the plan stops and is revised.
- **A full log.** The log is capped at 4 MiB, an agent can fill it by repeated runs, and a full log refuses runs above
  `block`. The owner rotates it. The attempt is written only when a change is about to be made, and nothing is written for
  an approval that already exists, which limits what an agent can add.
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

Revision 1 (2026-10-26): after the owner approved the plan, the security checkpoint of Increment D found the issues listed
in the Result. The plan was revised as described under "Assumptions and constraints". The revision was reviewed by the review
engine through the `ask-codex` bridge (model `gpt-5.6-terra`, effort medium) on 2026-10-26, at the owner's request: two rounds
of the bound of 3, not converged and not extended. Round 1: the `wb acknowledge` key duplicated two checkpoint keys (R1-F1),
Increment F had no spelling-probe step (R1-F2) and the HIGH-1 decision had no named file or owner checkpoint (R1-F3); all
applied. Round 2: the revision is not yet approved (R2-F1, rejected: true by design, only the owner approves) and Increment G
could not enable `ask` and `none` (R2-F2, applied, with a stop if the module declaration lacks a field). The text added for
R2-F2 and the other round 2 edits were not reviewed again. The reason recorded for R2-F1 says "install command" where it meant
`wb approve-plan`; decisions are recorded once and it stands as written. The owner has not approved the revision.

## Deferred work

- The other keys of the decision's table, each with its own preview digest, in later plans.
- A command that edits the table, if hand edits prove error-prone.
- A roadmap candidate for this work, if the owner wants one.
- Removal of the `checkpoint` lines of `wb settings` and the `stop` and `delegate` words, once nothing reads them.

## Result

### Increment A — Trial: can an `ask` prompt be answered remotely

Done by the owner and reported to the agent on 2026-10-26; the agent ran no trial step. Claude Code 2.1.310, repo head
`1a731fa`. The evidence note is in `docs/specs/harness-modules.md`, "An `ask` prompt answered from the remote channel". Observations: the prompt reached the remote side, a No given there refused the command and closed the terminal prompt, and the
`ask` rule beat auto mode. After review round 1 (finding: the remote Yes was unobserved), the owner repeated it: a Yes ran the
command. Round 2 found the side of the answers unstated; the owner then reported tapping Yes or No on the remote side only.
The stop condition did not trigger and the plan continues.

Not done, or different from the plan: the harness was not attached by the workbench (a hand-written `ask` rule was used in a
plain throwaway folder, so the rendering is not tested); the owner's global
`PermissionRequest` hook was not tested (none found in `~/.claude/settings.json` or `~/.claude/plugins`); a first rule that
did not match was replaced.

Security checkpoint: not reached (it is Increment D, step 1).

Review: two rounds by the `reviewer` agent (cap 3), both recommending "blocking findings". Round 1: the note overclaimed
the side of the answers (reworded), the remote Yes was unobserved (the owner repeated it), a process remark was removed;
details the reviewer could not see in the owner's pastes (command text, the "1. Yes / 2. No" numbering, the session's
"because you denied it") were kept, as they are in the pastes. Round 2: the side of the repeated Yes was unstated (the owner
then reported tapping on the remote side only), the unreported `ask-trial-3` text and "ran" were removed, and the repository
head and "auto mode" wording were corrected. A third round was not run on the text changed after round 2, which only records
the owner's statement; that is for the owner to ask for.

### Increment B — The levels table in the settings reader

Changed: `workbench/settings.py`, `workbench/settingscmd.py`, `tests/test_settings.py`, `tests/test_settingscmd.py`. The reader
accepts versions 1 and 2; `levels` is read only in version 2 (in version 1 it is an unknown entry, as before). `stop` and
`delegate` read as `block` and `delegated`; a key in both takes the stricter, with a note when they differ; a bad value, a
bad key or a `levels` that is not an object reads as `block`; `delegated` is kept for `approve-plan` only, and `ask` and
`none` are read but clamped to `block` with a note, since no key offers them before F and G. `effective` returns a `levels`
table and `checkpoints` follows it, so a bad entry cannot unlock delegation. `wb settings` prints a `level <key>: <level>` line
per declared checkpoint after the cap lines. Choices made: the seed stays at version 1 (the existing seed test asserts it),
so the owner changes `version` to 2 by hand to use `levels` (the spec says "version becomes 2"; Increment H must say how
that happens); keys in `levels` that no declared checkpoint names are noted and ignored until the registry of C.

Verification as run: tests written first and seen failing; `python3 -m unittest discover -s tests -p 'test_settings*.py'`
(83 tests OK); `python3 -B -W error tests/run_all.py` (4530 tests in 10 roots, OK; an earlier run failed two boundary tests
because a comment named a module, fixed); `git diff --check` clean; `python3 -m workbench check` no problems. Not run: the
plan check after the last edit.

Review: one round by the `reviewer` agent (cap 3), recommendation "no blocking findings". Applied: the key pattern now ends
in `\Z` so a trailing newline is invalid (finding 1, with a test); a test through `planapprovals.delegating` for the unlock path
(finding 2). Not applied: the redundant second note when a clamped entry meets a checkpoint reading (finding 3, acceptable),
and the undeclared-key note against the spec's "refused" wording (finding 6, same effect). Finding 4 is recorded above.

Committed as `498b224`.

### Increment C — Keys, offered levels and shipped defaults

Changed: a new `workbench/levels.py` and `tests/test_levels.py`; `workbench/settings.py`, `workbench/settingscmd.py`,
`tests/test_settings.py`, `tests/test_settingscmd.py`. The registry is built from `rules.OWNER_RUN` (a key `wb <command>`;
`approve-plan` is the checkpoint of that name), the process module's declared checkpoints, and the owner-run arguments of the
installed commands (`wb run <command> <argument>`), so no module is named in the installer. A floor id is never a key; a
`levels` entry naming one is a problem and is dropped. Each key offers `block`; only `approve-plan` also offers `delegated`;
no key offers `ask` or `none` yet (so `accept-decision` offers `block` only); every default is `block`. A level a key does not
offer reads as `block` with a note, and a key not in the registry is noted and ignored. `effective` takes the installed
commands and returns a level for every key; `wb settings` prints a `level` line per key (checkpoints first, then the
owner-run commands, then module arguments). Choices made: the drift test is that every `OWNER_RUN` command and every declared
checkpoint has a key (by construction the registry cannot miss one; a test pins it); `wb acknowledge` is a key beside the
`acknowledge-first-tier` and `acknowledge-second-tier` checkpoints. The shipped modules' own owner-run arguments were not
asserted in a test, because that would name a module in the installer's tests.

Verification as run: tests first and seen failing; `python3 -B -W error tests/run_all.py` (4548 tests in 10 roots, OK);
`git diff --check` clean; `python3 -m workbench check` no problems. Not run: the plan check after the last edit.

Review: one round by the `reviewer` agent (cap 3), recommendation "no blocking findings". Applied: the drift test now pins a
hand-listed set of owner-run keys, so a new `OWNER_RUN` command fails until it is listed (finding 1; the earlier test
recomputed the registry's own expression). `initialize` was diffed against HEAD and is identical. For Increment H (finding 2):
the spec says `accept-decision` offers `block` and `ask` and needs the "from the version that builds it" qualifier; the
shipped-defaults table must list `wb acknowledge`; the rule that a command reaching more than one key takes the strictest is
not built and must not be claimed built; the installer-interface text and `development.md` must document the new `level` lines.
Findings 3 and 4 need no change.

Committed as `dac9139`.

### Increment D — The log

Security checkpoint (step 1), 2026-10-26: the owner was asked and answered yes, review the design now. The `security-reviewer`
agent ran a design-stage review. It was read-only in effect: its scratch write was refused (the agent gate's scratch template is
the macOS path form, and this machine's is `/tmp/claude-1000/...`), so it ran no probe and nothing is "tested". It read `store.py`,
`safefs.py`, `settings.py`, `levels.py`, `delegation.py`, `planapprovals.py`, `approvalcmd.py`, `rules.py`, `gate.py`, `display.py`
and the specs. It did not read `declarations.parse_json`, `commands.owner_refusal`, the review-engine module or the attach code.
Findings, unjudged by the owner: HIGH-1 at `ask`/`none` the only barrier is a harness rule matching the command text, so a
path-qualified `wb` (the store's own `bin/wb`) or a shell edit of the harness file defeats it; MEDIUM-1 the store API has no
append, so "append-only" needs a new `safefs` call (`O_APPEND|O_NOFOLLOW`, regular file, one link, a single write of at most
1,024 bytes); MEDIUM-2 an agent can fill the log until every run above `block` refuses, since `delegate-approve-plan` is agent-safe
and nothing prunes it; MEDIUM-3 the rendering record must list every key, and a missing key must read `block`; LOW-1 a 12-character
digest can be ground (full or at least 32 characters, and cover the declaration and helper hashes and the project id); LOW-2 a
malformed `levels` key falls back to the default, which becomes `ask` for two keys in F and G; LOW-3 the key `wb run review-engine
extend` names a command, not a module. B and C: no loosening path found.

Not done: no test, code or commit for D. Several findings change the approved plan or the specs (the log's append call and
its bound, the digest length, the rendering record, the acceptance of the HIGH-1 limit). Per the plan, it stops here to be
revised and re-approved; nothing was widened.

Revision 1 was approved by the owner on 2026-10-26 and Increment D was then built.

Changed: `workbench/wbkit/safefs.py` (new `append_line` and `FullError`: one `O_APPEND` write of one line, no-follow,
non-blocking open, regular file with one link, a size limit checked before the write, fsync, nothing read); a new
`workbench/levellog.py` (`begin`, `finish`, `read`, `report`: tab-separated ASCII lines, identifier from `secrets`, key,
level and evidence validated, reason cleaned with `display.ascii_text` and cut to 200 characters, 4 MiB cap, a damaged
line a problem and never a refusal, a second outcome never replaces the first); `workbench/delegation.py` (the attempt is
written after every check and just before `planapprovals.add`, and only when no equal entry exists; the outcome follows on
every path; an unwritable attempt refuses with nothing recorded; an unwritable outcome after the approval prints to
standard error and exits 3); `workbench/settings.py` (a key that is not a valid name blocks the whole table);
`workbench/levels.py` (`RegistryError` for two declarations of one key; `wb acknowledge` is no longer a key, review
finding R1-F1); `workbench/settingscmd.py` (a `RegistryError` is a refusal); tests `tests/test_levellog.py` (new),
`tests/test_delegation.py`, `tests/test_settings.py`, `tests/test_levels.py`, `tests/test_settingscmd.py`,
`tests/test_attach.py`. The plan and `docs/specs/command-permissions.md` carry the uncommitted revision.

Choices made: the owner's reader is the functions `levellog.read` and `levellog.report`, not a command: no `wb` command prints
the log yet (the owner can read the plain-text file); the attempt for a delegated approval carries the evidence
`converged-<rounds>-of-<bound>`; the exit code 3 for an outcome that could not be logged is new. The harness-deny test is
a weak structural assertion (the store's `Edit(//store/**)` deny already covers every file below it).

Verification as run: the log, settings, levels and settings-command tests were written first and seen failing; the
delegation tests were written first but not run before the implementation, so their ability to fail is shown only by their
content. Afterwards: `python3 -B -W error tests/run_all.py` (4586 tests in 10 roots, OK); `git diff --check` clean;
`python3 -m workbench check` no problems. Not run: the plan check after the last edit; the security review of the built
code (asked before H).

Review: one round by the `reviewer` agent (cap 3), recommendation "no blocking findings"; it ran nothing. Applied: a write
that succeeded but could not be read back now logs `done` with a reason that says so, not `refused` (finding 1, with a
test); the short-write fragment and the approximate cap are documented in `safefs.append_line`, `levellog.py` and the spec
(findings 2, 3); `begin` bounds the key at 96 characters (finding 4); the reader rejects an attempt at `block` and a line
over 1,024 bytes, and says that `Operation.reason` is uncleaned (finding 5); the `delegate_approve_plan` docstring lists exit
3 (finding 6); tests for a review that has not converged, the read-back case and a `RegistryError` in `wb settings`, and a
test name fixed (finding 7). Not applied: the harness-deny check stays structural, and the delegation tests were still not
seen failing before the implementation. No `packages/` mirror of `safefs` exists (searched). Exit 3 is not yet in a spec or
`docs/development.md`; Increment H must add it. Final verification: `python3 -B -W error tests/run_all.py` (4590 tests in 10
roots, OK), `git diff --check`, `python3 -m workbench check` and the plan check, all clean.

Committed as `85b1514`.

### Increment E — Rendering and the drift check

Changed: a new `workbench/rendering.py` (the key-to-pattern map, the plan of rules per level, the table digest, the
record's form, its reader and `effective_level`); `workbench/rules.py` (`owner_run_command_patterns`);
`workbench/harnessplan.py` (`render_permissions` takes `ask_patterns` and `open_patterns`: an open pattern is not denied, an
ask pattern is asked, and also through the store's own `bin/wb`); `workbench/harnessstage.py` (`stage` builds the effective
table from the owner's settings, the process modules' checkpoints and the installed commands, renders from it, and returns
the record as `Staged.rendering`); `workbench/attach.py` and `workbench/install.py` (the record is written to the guarded
store before the files, on both the attach and the install paths); `workbench/check.py` (a permissions file that differs
from the record is a problem); `docs/specs/command-permissions.md` (`unruled`, and no record for a harness without
`permissions`); tests `tests/test_rendering.py` (new, 23 tests), `tests/test_attach.py` (the store gains the record),
`tests/test_install_attach.py`. Nothing yet calls `effective_level`: Increments F and G do.

Choices made: the record is written before the files, so a file that was not written leaves a hash that does not match and
`ask` and `none` read as `block`; a harness without `permissions` writes no record (absence reads as `block`); `unruled`
is a fourth value for a key with no command to match; `delegated` and `block` do not depend on the record; the `bin/wb`
pattern is added for `wb`-spelled ask patterns only; the harness identity is compared with the local manifest's `harness`
(the module name). The test seam is `levels._OFFERS`, because no key offers `ask` or `none` before F and G. `wb check` says
nothing when the file is missing (already reported) or when there is no record.

Verification as run: the tests were written first and failed on import; `python3 -B -W error tests/run_all.py` (4614
tests in 10 roots, OK, after two existing tests were updated for the new record and one check duplicate was removed);
`git diff --check` clean; `python3 -m workbench check` no problems on this repository. Not run: the plan check after the
last edit; a live harness (the synthetic harness only).

Review: one round by the `reviewer` agent (cap 3), recommendation "no blocking findings"; it ran nothing. Applied: tests for a
harness that provides no permissions (no record), a record with no local manifest, a symbolic link in place of the harness
file, a failure after the record is written (the keys stay at `block`), and the rules with no levels table (the old rules);
the module docstring now says the record names the module and not the package (finding 2). Open, for the owner (finding 3):
the spec says a stale record is repaired by attaching again, but `wb attach` refuses a clone that already records a harness,
so after a table or module change in an attached clone the owner has no command that restores `ask` or `none`; they read
`block`, which is safe. A fix (re-render, or a command to rewrite the record) is not in this plan and needs the owner's
decision. Increments F and G must build the table exactly as `harnessstage.stage` does or they always get `block`.
`wb check` can report a false difference in a clone that did not write the last record. Final verification: `python3 -B -W
error tests/run_all.py`, `git diff --check`, `python3 -m workbench check` and the plan check (below).

Committed as `2f12a6a`.

### Increment F — `approve-plan` at `ask` and `none` (stopped at step 0, the owner checkpoint; no code written)

Step 0, 2026-10-26: the decision `docs/decisions/2026-10-26-ask-level-spelling-limit.md` was drafted as `Proposed` with the
`draft-decision` skill and listed in `docs/decisions/README.md`. It states the HIGH-1 limit, the mitigations built in D and E,
the probe required after F, the alternatives rejected and the consequences, including the open gap that no command restores
`ask` or `none` in an attached clone after a table or module change. Only the owner accepts it. F stops here until the
owner has accepted it and says so; the Result will then record the acceptance and its date. Until the file is committed,
`python3 -m workbench check` reports one problem (the index row points to a file git does not track), which commit clears.
Nothing else was changed.

The owner asked for the order of F's code and its probe to be explicit: the decision now says F's code is committed first and
the probe is its last step, with `ask` not offered as a default to anyone else until the probe is recorded. The plan's text
is unchanged, because changing it would need a new approval. On 2026-10-26 the owner asked the agent to approve the decision;
the agent did not, because only the owner accepts a decision, and committed it as `Proposed`.

Step 0 outcome, 2026-10-26: the owner accepted the decision `2026-10-26-ask-level-spelling-limit`. The owner told the agent in
the session to make the status edit ("make the edit for me, accepted"), so the agent edited the status line and the index row
as the owner's scribe and did not decide anything. The condition of Increment F is met.

Committed as `1a50529` (the acceptance).

Step 1 onward, 2026-10-26: F's code. Changed: `workbench/planapprovals.py` (`plan-status <plan> --digest`, the read-only preview
that prints what an approval binds and a 32-character digest; the remote forms of `approve-plan`: `<plan> --digest <32>` at
`ask` and `<plan>` at `none`, each reading the level from `rendering.effective_level`, recomputing the digest in its own
process, re-checking the plan, writing the attempt only when no equal approval exists and just before the record, and an
outcome on every path; the terminal path unchanged); `workbench/rendering.py` (`current_table`, the table as the installed
modules give it now); `workbench/levels.py` (`approve-plan` offers `ask` and `none`); `workbench/levellog.py`
(`finish_refused`); `workbench/cli.py` (the two grammars); tests `tests/test_approve_levels.py` (new, 32 tests),
`tests/test_levels.py`, `tests/test_settings.py`. The digest covers the project identifier, the declaration and helper
hashes, the plan's path, its region hash and what the approval does not cover. Exit 3 means the approval was recorded but
its outcome was not logged.

Choices made, and one departure from the plan: the plan's step 4 (change the registry default of `approve-plan` to `ask`) is
NOT done. The accepted decision `2026-10-26-ask-level-spelling-limit` says `ask` is not offered as a default to anyone else
until the spelling probe is recorded, so the shipped default stays `block`; the mechanism (`levels._DEFAULTS`) and its test
are in, and the flip is a one-line change after the probe. The preview is an option of `plan-status` (agent-safe), not a new
command. A project that is not attached, or whose record is stale, reads `block` and the remote forms refuse with the
terminal-only message.

Verification as run: the tests were written first and failed for the missing feature (25 of 32); `python3 -B -W error
tests/run_all.py` (4652 tests in 10 roots, OK); `git diff --check` clean; `python3 -m workbench check` no problems. Not run:
the plan check after the last edit; the spelling probe (step 5, owner steps); a live harness.

Review: one round by the `reviewer` agent (cap 3), recommendation "no blocking findings"; it ran nothing. Applied: an interrupt
of the run without a terminal exits 130 and logs a `refused` outcome (finding 2, with a test); a digest given where the level
is not `ask` gets a message that says what is needed, still containing "owner-run" (finding 4, with a test). Not applied:
the harmless over-log in a race between the equal-entry check and `add` (finding 3); a positive terminal approval is covered
by older tests, not this file (finding 5); a v1 settings test through `effective_level` (finding 1, covered by the default
test through attach). For Increment H: the spec's shipped-defaults table must say the flip of the `approve-plan` default waits
for the probe. Final verification (below).
