# Specs that say what is built, and agree with each other

Status: Completed
Created: 2026-10-29
Candidate: workbench-v1#docs-cleanup-after-reset
Specs: groundwork, code-work, repository-boundary, module-contract, module-boundary, harness-modules, trust-and-approval, command-permissions, terms, review-engine, action-review, model-bridge, remote-runner, safe-git

## Goal

Six read-only reviewers audited the specifications, the decision records, the roadmap, the base and the modules on 2026-10-29,
after the owner reset the global Claude configuration. I confirmed the main findings by reading the files. This plan fixes the
first two kinds of drift they found: text that calls built work unbuilt or a design a proposal, and passages that contradict each
other or the module they describe. The other kinds (the definitions in `terms.md`, text that leaned on the former global setup, the
inventory and the roadmap) are the second plan under the same candidate, `2026-10-29-terms-inventory-and-roadmap-cleanup`, which
starts after this one is complete.

## Scope

- Specs under `docs/specs/`, in three increments. Every fix is found by reading the statement and the code or module it describes in
  the same increment; a line number from the audit is a pointer and not a license.
- A statement is corrected to what the module or the code does. Where a spec and a module disagree in a way that looks like a
  defect in the module, the disagreement is reported to the owner and not fixed here.
- The status line of `terms.md` and `harness-modules.md` only, in Increment B. The definitions in `terms.md` are the second plan.

## Non-goals

- Any change under `packages/`, any code and any test. That includes the `verilog` module description and the seeded plans README,
  which are module files and wait for the plan that releases the packages.
- The citations of `AGENTS.md` sections that no longer exist (`command-permissions.md`, `mempalace.md`, `knowledge-tools.md`,
  `code-work.md`). The plan that restores the base `AGENTS.md` sections fixes them, so this plan leaves them alone to avoid fixing
  them twice.
- The rule for who accepts a decision, the identity convention in the module READMEs, and the `ask` for `accept-decision`: the policy
  plan and the approval-identity plan.
- Setting a spec's status to `Current`. Only the owner approves a spec, so a status change is listed for the owner and made only
  on their word.
- Editing an accepted decision record, or the heading format of the roadmap candidates (the owner's call).
- Text that depends on the former global configuration, the inventory, the terms and the roadmap: the second plan. One exception: a
  single false statement about the former configuration in a file this plan already edits is corrected here (the sentence in
  `code-work.md` that the superpowers plugin "is still enabled", Increment A step 2). Passages that rest on such a statement are the
  second plan's.

## Assumptions and constraints

- Specs are living and are edited in place (`docs/specs/README.md`). A spec written by someone other than the owner is untrusted
  until acknowledged, so the owner reads each increment's diff before it is accepted.
- The document checks (`wb check`, which runs the groundwork helpers, and `wb run code-work check` for plans) do not read meaning,
  so each increment also names a search that must come back empty.
- No increment touches a package, so no shipped approval goes stale and the command gate stays open throughout.
- A command line that names a reserved word can be refused by the command gate (a path containing `reset`, `remove`, `approve-plan`
  or similar). If a spec's name or a path trips it, stop and ask the owner, and do not work around it.
- Each increment is one reviewed local commit. Review is a read-only reviewer pass of that increment's diff.

## Completion criteria

1. Every statement named in an increment is corrected, or reported to the owner as a decision, and the search the increment names
   finds none of the old wording.
2. `wb check` and `wb run code-work check` report no problems.
3. `git status` shows only documents changed, and `wb verify packages/workbench` runs with no refusal.

## Increments

### Increment A — Built and unbuilt, in the module-defining specs

**Outcome:** `groundwork`, `code-work`, `repository-boundary`, `module-contract` and `module-boundary` agree with the modules and
with each other about what is built.
**Dependencies:** none.
**Affected areas:** `docs/specs/groundwork.md`, `code-work.md`, `repository-boundary.md`, `module-contract.md`, `module-boundary.md`.
**Steps:**
1. `groundwork.md`: the summary rows "helpers: none" and "ships: nothing code-bearing", and the sentences that say the module "ships
   no code", contradict the two read-only check helpers (`doccheck`, `refcheck`) that its `module.json` ships and `wb check` runs.
   Read `module.json` and correct each place.
2. `code-work.md`: the `requires` row names soft requirements (`peer-review`, `permissions`) that `module.json` does not declare;
   the helper's subcommand list and the `approval` row omit `delegable`; the note that "the superpowers plugin is still enabled in
   `~/.claude`" is false after the reset; the header and the lines about increment F of the delegated approval say it is unbuilt, so
   read the plan `2026-10-23-delegated-approval` and its Result and correct them. Do not touch the lines that cite `AGENTS.md`.
3. `repository-boundary.md`: the store layout says "(plan approvals are not built yet)"; they are built. Correct it.
4. `module-contract.md`: "`wb check` does not run it yet" for `checks` contradicts the sentences that say it does; the sentence that
   the installer never runs a helper should read as `module-boundary.md` says it will be corrected (never at install, a pinned one
   at use time); the `commands` row omits `levels` and `preview`, which the spec defines later.
5. `module-boundary.md`: the status and the decision link text say the document-check decision "stays in force" and is "to be
   superseded"; `2026-10-21-installer-runs-document-checks` is `Superseded by 2026-10-21-module-code-lives-in-modules`. Correct them.
**Verification:** a search of the five files finds none of the old phrases named above; `wb check` and `wb run code-work check`
report no problems; `git status` shows only those five files.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-specs-built-state-cleanup#A`.

### Increment B — Harness, trust and permission specs

**Outcome:** `harness-modules`, `trust-and-approval`, `command-permissions` and `terms` agree with the code that renders and enforces
permissions, and say what is built.
**Dependencies:** none.
**Affected areas:** `docs/specs/harness-modules.md`, `trust-and-approval.md`, `command-permissions.md`, `terms.md` (status lines only).
**Checkpoint before the steps:** this increment edits the specs that describe the permission, approval and command-gate model. The
module that provides `security-review` is installed, so before step 1 I ask the owner whether to run a security review, and run one
only if the owner asks. The answer is recorded in the Result.
**Steps:**
1. `harness-modules.md` and `terms.md`: the status lines say implementation has not started, and `terms.md` calls the system one
   "that does not exist yet"; the Claude harness is built. Reword to say what is built and what stays a proposal (a second harness).
2. `harness-modules.md`: the three decisions `project-guarantees-a-floor`, `declared-agent-confinement` and
   `installer-reads-global-settings-on-request` are called "all `Proposed`"; all three are accepted. The owner-run deny list names ten
   commands and omits `rerender` and `approve-plan`, which `rules.OWNER_RUN` holds. The statement that the owner's `allow` rules are
   never read or written is true of attach and false of `rerender`, which preserves them verbatim (read `harness-rerender.md`).
   The list of hooks the installer renders omits the command gate.
3. `trust-and-approval.md`: the delegated plan approval is called "designed ... and not built" and a "proposal" at two places and
   built at others (read "As built, increment D" and the header); the sentence that `Bash` and commit-time gates are deferred
   predates the built command gate; the owner-run list omits `rerender`; the two-value checkpoint setting (`stop`, `delegate`) is
   described without a pointer to the four levels in `command-permissions.md`. Correct each.
4. `command-permissions.md`: two passages state the owner's own settings table and one clone's rendering as current ("the owner's
   table now", "out of date") when the shipped default is `block` and `wb rerender` refreshes a stale clone; keep the facts as dated
   provenance and state the shipped default. The agent-safe and owner-run key lists omit `wb preview upgrade`, `wb preview add`,
   `wb preview rerender` and `wb rerender`; add them.
**Verification:** searches for "all `Proposed`", "not built" beside the delegated approval, "implementation has not started" and
"does not exist yet" in these files come back empty; `wb check` and `wb run code-work check` report no problems; only these four files
changed.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-specs-built-state-cleanup#B`.

### Increment C — The module specs

**Outcome:** `review-engine`, `action-review`, `model-bridge`, `remote-runner` and `safe-git` say what their modules do, and one
figure or name appears once.
**Dependencies:** none.
**Affected areas:** `docs/specs/review-engine.md`, `action-review.md`, `model-bridge.md`, `remote-runner.md`, `safe-git.md`.
**Steps:**
1. `action-review.md`: the reason limit is 300 characters at two places and 500 at one; correct the 500. The capability name
   `action-review` is called "a proposal" and "still the owner's to confirm" though the module provides it; the table of future
   collectors names `remote-runner describe` commands that the module does not declare, so mark that "not built". The cutover
   sections that describe the owner's old approver program as live get a dated note that it was part of the former global
   configuration, reset on 2026-10-29.
2. `review-engine.md`: the argument count reads "fourteen now" at one place and "the thirteenth argument" at another; the module
   declares fourteen, so correct the history to say which was added when.
3. `model-bridge.md`: the capability name `model-bridge` is called "still a proposal" though two accepted specs require it and the
   module provides it. Correct it or list it for the owner.
4. `remote-runner.md`: the project file is said to move from `~/.claude/remotes.toml` and `.claude/remote-runner.toml`; add a dated
   note that the user-level file is gone after the reset. The status reads `Current` while the spec admits an external program does
   not read the project file it gives; add that to the status line as a limit.
5. `safe-git.md` and `remote-runner.md`: one spelling of the re-release command (`wb release-approvals`). The safe-git passages
   that record the old approver's rules and hashes stay as provenance.
6. **For the owner, not done here:** whether `review-engine.md` and `action-review.md` should now read `Current`. List them in the
   Result with what each still marks as unbuilt, and change a status only on the owner's word.
**Verification:** a search for "at most 500", "fourteen now", "still a proposal" and "is a proposal" in these files finds none of the
old wording; `wb check` and `wb run code-work check` report no problems; only these five files changed.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-specs-built-state-cleanup#C`.

## Verification for the plan as a whole

- `wb run code-work check` reports no problems on this plan before it goes to the owner, and again after any edit.
- After the last increment, `git status` shows no file changed outside `docs/`, and `wb verify packages/workbench` runs with no
  refusal, so no shipped approval went stale.
- A read-only reviewer pass of each increment's diff, and the owner's read of each diff, before the commit is accepted.

## Risks and sensitive actions

- Specs are the project's authority. A wrong correction is as harmful as the drift it fixes, so each is made from the module or code
  read in the same increment, and a spec and a module that disagree in a way that looks like a module defect are reported and not
  fixed.
- A spec status can imply the owner's approval. This plan never sets `Current`; the owner does, and only for the specs named.
- A wide documents-only change is easy to review badly. Each increment is limited to named files and a named search, and the owner
  reads the diff before it is committed.
- The command gate matches command text, so a spec path that contains a reserved word can stop a command. If one does, stop and ask.
- No code, package, shipped approval or permission is touched.

## Review record

Plan review by Codex through the `ask-codex` bridge (model `gpt-5.6-terra`), round 1 of 3. A first attempt on the single undivided
plan was refused by the bridge (`reply_too_large`, no round spent), so the plan was split in two under one candidate. Outcome: two
findings, both applied.

- **Applied (major).** A checkpoint before the steps of Increment B asks the owner whether to run a security review of the edits to
  the permission, approval and command-gate specs. A review runs only if the owner asks.
- **Applied (minor).** The scope states one exception to the deferral of former-setup text: a single false sentence in a file the
  plan already edits (the superpowers plugin sentence in `code-work.md`) is corrected here.
- **Not asked for.** A second round.

## Deferred work

- The terms, the text that leaned on the former global setup, the inventory and the roadmap: the second plan under this candidate.
- The `AGENTS.md` citations, the rule for who accepts a decision, the identity convention in the READMEs, the seeded plans README,
  and the `verilog` module description: the policy and module-asks plan.
- The heading format of roadmap candidates, an index of specs and decisions, and the `Status:` of two approved plans: the owner's
  call, not made here.

## Result

**All three increments are done.** Their commits carry the trailers `Plan: 2026-10-29-specs-built-state-cleanup#A`, `#B` and `#C`.

### Increment A

- **Done, in the five named specs.**
  - `groundwork.md`: the two table rows and the two "ships no code" sentences now say the module ships the read-only check helpers
    `doccheck` and `refcheck`.
  - `code-work.md`: the `requires` row declares no soft requirement; `delegable` is in the helper and `approval` rows; the plugin
    sentence says it is no longer enabled because the user-level configuration was reset on 2026-10-29; the three increment F
    statements say it landed (two security passes, fixes, the approvals released by the owner).
  - `repository-boundary.md`: the store layout has a `plan-approvals` entry in place of "not built yet".
  - `module-contract.md`: the helper sentence, the `checks` note and the `commands` row are corrected.
  - `module-boundary.md`: the status, the link text and the body say it is built and the document-check decision is superseded.
- **Beyond the listed steps, in the same files and of the same kind, after the review.** `code-work.md`: the checkpoint-settings
  bullet said `delegate` has no effect, now marked as true when built; "once the delegated approval is built" now reads "since it was
  built". `module-contract.md`: the `approval` row now lists `delegable`.
- **Verification as run.** A search of the five files for the old wording finds none; `wb check` and `wb run code-work check` report
  no problems; `wb verify packages/workbench` ran with no refusal; `git status` showed only documents changed.
- **Review.** One read-only reviewer pass of the increment: no blocking finding, and every factual claim I checked was confirmed,
  including that increment F landed, the plan names and statuses, and that the installer has no `doccheck`, `refcheck` or `refindex`
  file. It raised three non-blocking leftovers, all fixed as above. It could not see a diff and did not rerun my searches.
- **Left for the owner.** The `delegated-approval` plan's own Result still says increment F is "not yet committed"; it is a completed
  plan, so I left it. The lines that cite `AGENTS.md` sections in `code-work.md` were not touched, as the plan says.

### Increment B

- **Security review.** The checkpoint asked the owner, on 2026-10-29, whether to run a security review of the edits to the
  permission, approval and command-gate specs. The owner chose to skip it. In its place the reviewer was given eight
  security-property claims to verify against the code, and it confirmed all eight.
- **Done.**
  - `harness-modules.md` and `terms.md`: the status lines say the Claude harness and the installer are built and a second
    harness is not. "All `Proposed`" now says the three decisions are accepted. The owner-run deny list gains `rerender` and
    `approve-plan`. The `allow` rules text says attach never reads or writes them and `rerender` carries them, as
    `workbench/rerender.py` and `harness-rerender.md` show. The hooks list gains the command gate.
  - `trust-and-approval.md`: the delegated record is built; a paragraph explains how `stop` and `delegate` map to the four levels
    and the precedence of table entry, checkpoint reading and shipped default; `wb rerender` is in the owner-run list; the edit gate
    sentence says the command gate is the separate, built shell hook; the delegated-formats sentence says format 2 is built.
  - `command-permissions.md`: the dated snapshots say 2026-10-27, and the clause that this clone's `draft-decision` skill was out
    of date is corrected, because the clone has since been re-rendered; the key lists gain `wb rerender` and the preview keys.
- **Beyond the listed steps, after the review.** `command-permissions.md`: the "Draft a roadmap ..." row now agrees with the corrected
  row below it; `wb preview rerender` is in the `wb settings` key list; `run`, a dispatcher word that is not a key, is out of the
  Coverage list. `trust-and-approval.md`: the deferral of a shell or commit-time gate is stated as the source plan stated it, as
  conditional.
- **Verification as run.** A search for the old status and snapshot wording finds one legitimate use ("the effective table now" in
  a rule); `wb check` and `wb run code-work check` report no problems; `wb verify packages/workbench` ran with no refusal; `git
  status` showed only the four specs changed.
- **Review.** One read-only reviewer pass: no blocking finding. It confirmed owner-run lists against `rules.OWNER_RUN`, the built
  command gate, `rerender` and `allow`, the built delegated approval and format 2, the precedence rule and defaults against
  `levels.py` and `settings.py`, and the status lines. Its four non-blocking points are fixed as above. It could not run git or
  the checks and did not compare the two `draft-decision` skill files byte for byte.
- **Left for the owner.** Whether `harness-modules.md` and `terms.md`, still `Status: Current`, need re-approval after their status
  text changed: I changed what they say is built, not what they require.

### Increment C

- **Done.**
  - `action-review.md`: the verdict `reason` limit reads 300 characters everywhere, as the helper enforces (`MAX_REASON`); the two
    statements about the capability name say the built module provides it and the owner has not confirmed it as final; the
    collectors table marks `remote-runner describe` as not built; a dated note says the approver program, the global
    `claude-workflow` program, `safe-committer` and `amend-message` belonged to the former user-level configuration, reset on
    2026-10-29.
  - `review-engine.md`: the argument count is stated in order, twelve at first, then `convergence` (the thirteenth), then `preview`
    (which came later); the sentence about the shipped approval being stale is in the past tense. The audit called the count a
    contradiction, but it was consistent and only easy to misread.
  - `model-bridge.md`: the status line and Open questions say `ask-codex` provides the capability name, `review-engine` and
    `action-review` require it, and the owner has not confirmed it as final.
  - `remote-runner.md`: a dated note says the user-level hosts file went with the reset and that neither listed path holds one,
    which I checked by listing both directories on 2026-10-29. The status line already stated the limit that the external program
    does not yet read the project file from the path the spec gives, so that step needed no edit.
  - `safe-git.md`: the spelling `wb release-approvals`.
- **Verification as run.** A search of the specs for "at most 500", "still a proposal" and "fourteen now:" finds only legitimate
  uses (other fields that are truly 500 characters, a count of changed paths, and the rewritten sentence); `wb check` and
  `wb run code-work check` report no problems; `wb verify packages/workbench` ran with no refusal; `git status` showed only the
  five specs changed.
- **Review.** One read-only reviewer pass: no blocking finding, and it verified the 300 limit against the helper, the module
  declarations, the spelling and the statuses. Its non-blocking points: the `preview` ordinal rested on declaration order only, so
  it was removed; a tense mix, fixed; and the approver passages in `action-review.md` that still read as live (see below).
- **For the owner, step 6, not changed.**
  - `action-review.md` stays `Draft`. Its status line says the owner has not read the engine sections and that the push rule, the
    owner's hook, the log writer, the labelled set, the report and the shadow period are not built.
  - `review-engine.md` stays `Draft`. Its status line still says it was written before the module existed; the module is built. It
    marks one thing unbuilt: the personal setting for bridge, model and effort (decision 5 of the accepted record).
  - Setting either to `Current` is the owner's act, and I changed neither.
  - The sections of `action-review.md` on the shadow period and the cutover (around lines 43 to 61, 267, 478 to 483 and 513 to 514)
    still describe the approver as running. The dated note at the top says it is gone; whether to point each section at the note
    is the owner's call and is not in this plan.
  - `safe-git.md` says the edit gate refuses every edit while the package's approval is stale. The refusal I saw was the command
    gate refusing shell commands; I did not test the edit gate in that state, so the sentence is unchanged and unverified.
