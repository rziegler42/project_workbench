# Adopt an existing repository: install the workbench into a directory that has content

Status: Completed
Created: 2026-10-25
Candidate: workbench-v1#adopt-existing-repository
Specs: installer-interface, repository-boundary, trust-and-approval, harness-modules

## Goal

Give the installer a way into a repository that already has content, without overwriting or editing any file already
there, and use it to make this repository an installed project. After this plan the workbench's own gates (the edit
gate, the plan check, `wb approve-plan`) apply to the workbench's own work, which today the owner enforces in session
(`AGENTS.md`, "Bootstrap").

Discovery for this plan (2026-10-25, by reading; no discovery tool is installed) found:

- **The installer refuses populated directories by design.** `workbench/target.py` (`_classify`) returns `new-empty` for an
  empty directory, `new-git` for one holding only `.git`, and `existing` only with `.workbench/manifest.json`; anything
  else is refused (`docs/specs/installer-interface.md`, "States of a target"; decision
  `2026-10-20-target-decided-by-state`). This repository has 390 tracked files, `.claude/`, `CLAUDE.md` and
  `.template-manifest`, so it is refused today.
- **`install` creates files exclusively.** "A path that already exists, tracked or not, is a conflict for the owner"
  (`installer-interface.md`, "Rules common to the project commands"). Seven seeded paths exist or may exist here
  (`self-hosting` recorded them: six `diverged`, one `absent`), so the install plan cannot simply be run on this
  repository.
- **The parts adoption needs already exist.** `upgrade` classifies a present seeded file as **skip** and a slot block
  with no entry as **create** where its marker is present or **append** (on approval) where it is not
  (`repository-boundary.md`, "Classification on upgrade"). `attach` leaves a file that equals the planned bytes and
  reports any other as a conflict (`workbench/attach.py`). Adoption therefore needs a new entry state and a plan that
  keeps what is there; it does not need a new way to edit files.
- **Harness files already exist here.** `CLAUDE.md` and `.claude/remote-runner.toml` are untracked, excluded and written
  by the old template. `install` ends with `attach`, which would meet them as conflicts, so adoption must not attach.

When this plan is done:

1. `wb adopt` (and `wb preview adopt`) installs the selected modules into a directory that has its own real `.git`, has
   content and has no `.workbench`. It creates only what is missing and writes nothing into an existing file.
2. For each path that already exists the preview says what happens: a seeded file is **kept** and recorded as the
   project's own with the hash of the bytes there; a path the module owns, or one of the wrong type, refuses the whole
   command. A slot block whose file exists is **not filled**, and the preview names the file, the slot and the
   `wb upgrade` that offers it.
3. This repository is an installed project with its harness attached: `.workbench/` and its manifest exist, the owner has
   run `wb adopt` and then `wb attach` on it (resolving any existing harness-file conflict first), `wb check` passes and
   the edit gate is active here. (Increment F; owner-run.) Without the attach step the repository would be installed
   but not gated, because the gate is rendered into the harness files by `attach`.
4. A decision record and spec changes state all of the above, and the decision is accepted by the owner.

## Scope

- Increment A: `docs/specs/installer-interface.md` and `docs/specs/repository-boundary.md`, and one new decision record
  (`Proposed`). No code.
- Increment B: `workbench/target.py` (the new state) and `workbench/installplan.py` or a new module for the adoption plan,
  `workbench/preview.py` (`preview adopt`), `workbench/cli.py`, their tests.
- Increment C: the write path (`workbench/install.py` or a sibling), the unfinished-write marker and `recover` for it,
  the manifest, baselines and store record, `adopt` added to the owner-run list in `workbench/rules.py` (the harness
  deny rules; `workbench/` is the installer, not a module tree), and their tests.
- Increment D: a security review of B and C, requested by the plan, with its findings recorded here and fixed in B or C.
- Increment E: tests across `upgrade`, `acknowledge`, `attach` and `check` on an adopted project, and the
  documentation in `docs/development.md` and `README.md`.
- Increment F: running `preview adopt` on this repository (me), `wb adopt` and `wb attach` (the owner), then the files the
  adoption creates.

## Non-goals

- Overwriting, replacing or editing any existing file, including adding a slot marker or appending a block to one.
  Filling the blocks of an existing seeded file is `wb upgrade`'s existing, approved behavior and is not changed here.
- Running `attach` from `adopt`. `attach` stays its own owner-run command; Increment F runs it on this repository.
- Running git, reading `.git/config` or any other repository configuration, or deciding anything from git state
  (`2026-10-20-target-decided-by-state`).
- Adopting a directory without its own real `.git`, a worktree or submodule `.git` file, or a symlinked target.
- Reconciling the text of this repository's `diverged` seeded files with the seeds. Each file is kept as it is.
- Migrating projects made from the old template (roadmap, Deferred).
- Changing a module's behavior. A module test that lists the owner-run commands may need `adopt` added (see C); if so
  its shipped approval goes stale and `release-approvals` is the owner's to run, which the plan records and does not do.

## Assumptions and constraints

- Python 3.11 minimum, standard library only. The installer root's tests run with
  `env PYTHONPATH=.:tests python3 -B -W error -m unittest discover -s tests -p 'test_<name>.py'`; the full suite is
  `python3 -B -W error tests/run_all.py` (about 4 minutes, in the background). Document checks run from the module
  source: `env PYTHONPATH=workbench python3 -B packages/workbench/groundwork/helper/doccheck` and `.../refcheck`.
- Tests never touch the real store (`tests/support.py`, `tests/support_install.py`). Only `preview adopt` is run on this
  repository by me; `adopt` is owner-run and terminal-only like `install` (`2026-10-20-preview-then-owner-run-write`).
- The adopted target is untrusted content. Every check reads files itself, without following links and without git, as
  the existing target rules require.
- This plan changes `workbench/` (the installer, including `rules.py`), not a module tree, so no shipped approval is
  expected to go stale. The deny rules are rendered from `workbench/rules.py`; the `claude` module's test file mentions
  owner-run commands and may list them, which C checks. If a module tree changes, the approval goes stale and the owner
  runs `release-approvals`.
- Discovery tooling: graphify: skipped — not installed in this project. The scope was found by reading the roadmap entry,
  `target.py`, `installplan.py`, `install.py`, `attach.py`, both specs, the target decision and the `self-hosting` plan.
- Not verified yet, and each is a step below that fails loudly if wrong: that `upgrade` run on an adopted project
  appends the missing blocks as the spec's classification says (D); that `check` and `acknowledge` accept a manifest
  whose seeded hashes are those of existing files (D); and how many existing-file cases `unfinished` and `recover` must
  learn (C).

### Choices (made by me; the owner may change any)

1. **A new command, `adopt`, not an option on `install`.** `install`'s promise is "a new project, nothing else", and
   several tests and the spec pin it. A separate verb makes the riskier operation visible in the command line, the
   preview and the owner's terminal. The alternative, `install --adopt`, changes the meaning of a command the owner has
   learned to trust.
2. **Adoption never edits an existing file.** The cost is a second step: the blocks that belong in an existing
   `AGENTS.md` or `docs/README.md` are filled by `wb upgrade`, which already offers an append on approval. The
   alternative, appending during `adopt`, would put the first edit of a hand-written file inside the riskiest command.
3. **A kept seeded file is recorded with the hash of the bytes there**, as owner class `seeded`. The manifest records the
   bytes the installer last saw, and "seeded with an entry is skip always" already means a later edit changes nothing.
   Recording the seed's hash instead would say the file is something it is not.
4. **`adopt` requires the target's own real `.git` directory.** A populated directory with no `.git` is not a repository,
   and the installer does not initialize one next to someone's files.
5. **`adopt` does not attach; the gate comes from the attach step that follows.** Existing harness files are the owner's.
   After `adopt`, `wb attach` runs its existing rule: equal bytes are left and reported, other content is a conflict
   listed with nothing written, and the owner resolves it by hand. Increment F schedules that step, because the edit gate
   is rendered into the harness files and is not active before it.
6. **Every `diverged` seeded file of this repository is kept as it is.** The roadmap says the disposition of each is
   decided here; the decision is "kept, text not reconciled". Reconciling any file is a later, ordinary edit.
7. **One plan, with a stop after A.** The design (A) needs the owner's reading and acceptance before code (B to D) is
   written. I do not start B until the owner has accepted the decision and approved the spec edits. The alternative is two
   plans (design, then build); I kept one so the candidate has a single completing plan.
8. **F is owner-run and last.** Running `adopt` and `attach` on this repository adds `.workbench/` (many files) and
   harness files to a repository whose tests and checks have never seen them. It is a separate increment so a failure there
   cannot be mistaken for a defect in B to E.
9. **The security review is an increment of the plan (D), not an option.** The roadmap candidate requires one. The
   owner's approval of this plan and the owner's "start d" are the request; it runs as an independent review and its
   findings are untrusted until I have checked each. The alternative, leaving it optional, could complete the candidate
   without meeting its boundary.

## Completion criteria

1. The specs state the `adopt` command, the adoptable target state and the kept, refused and not-filled outcomes, and the
   decision record exists and is accepted by the owner.
2. `wb preview adopt` and `wb adopt` exist. On a scratch repository with content they create only missing files, leave
   every existing file byte-identical (checked by hash), refuse each case the specs list, and record kept seeded files
   with their own hashes.
3. A test shows an adopted scratch project passes `check`, that `upgrade` offers the blocks the adoption did not fill,
   and that `attach` behaves as Choice 5 says.
4. A part-way failure leaves the unfinished-write marker and `recover` removes only what `adopt` created.
5. A rendered harness denies `adopt` in every spelling `install` is denied in, while `preview adopt` is not denied; tests
   show both.
6. A security review of `adopt` has run, and every finding is recorded in this plan as fixed, rejected with a reason, or
   deferred by the owner.
7. This repository holds `.workbench/` and a manifest written by `wb adopt` run by the owner, `wb attach` has been run by
   the owner with any existing harness-file conflict resolved, `wb check` passes there, the edit gate is active (a
   gated edit is refused or prompted as the spec says, shown by the harness's own check), and the full suite is green with
   no new skip.
8. `doccheck`, `refcheck` and `git diff --check` print nothing.

## Increments

### Increment A — Specification and decision

**Outcome:** the specs and a decision record say what `adopt` is, before any code exists.
**Dependencies:** none.
**Affected areas:** `docs/specs/installer-interface.md` (the states table, rule 9, `install`'s "Needs", a new `adopt`
section, the exit codes and the command table), `docs/specs/trust-and-approval.md` and `docs/specs/harness-modules.md`
(`adopt` joins the list of owner-run commands every harness denies), `docs/specs/repository-boundary.md` (an owner-class
note: a kept seeded file and its hash; the acceptance criteria),
`docs/decisions/2026-10-25-adopt-an-existing-repository-without-editing-it.md`
(new, `Status: Proposed`) and `docs/decisions/README.md` (its index row).
**Steps:**
1. States table: add the adoptable state (own real `.git`, content, no `.workbench` entry of any kind, no unfinished
   marker) and say `install` still refuses it, with the message naming `adopt`. Say what a directory without `.git`, with
   a `.git` file or link, or with any `.workbench` entry does.
2. `adopt` section: arguments (the same as `install`), needs, reads and checks in order, the outcome per path (create,
   keep, refuse, not filled), what is written and in what order, that it does not attach and says so, the exit codes, and
   that an agent may run `preview adopt` but not `adopt`.
3. Owner-class note and acceptance criteria in `repository-boundary`: an adopted manifest, the kept seeded hash, and that
   an adopted project is an existing project for every other command.
4. The decision record: context (the refusal and why it is right), decision (Choices 1 to 5), alternatives (option on
   `install`; appending during `adopt`; recording the seed's hash; running `attach` from `adopt`), consequences, and
   verification (built in B to D). It stays `Proposed`; accepting it is the owner's act.
5. Run `doccheck`, `refcheck` and `git diff --check`.
**Verification:** the three checks print nothing; the specs and the decision name the same cases.
**Evidence:** the one local commit, trailer `Plan: 2026-10-25-adopt-existing-repository#A`. **Stop here** until the owner
has read the spec edits and decided the record.

### Increment B — The adoptable state and `preview adopt`

**Outcome:** `wb preview adopt` plans an adoption and writes nothing.
**Dependencies:** A, and the owner's acceptance of the decision.
**Affected areas:** `workbench/target.py`, a new `workbench/adoptplan.py` (or `installplan.py` if it fits), `workbench/preview.py`,
`workbench/cli.py`, `tests/` (new `test_adopt_target.py`, `test_adopt_preview.py`).
**Steps:**
1. Tests first, each seen to fail: `_classify` returns the new state only for a real `.git` plus content plus no
   `.workbench`; it refuses a `.git` file or link, a `.workbench` of any type, a symlinked target, the home directory, the
   store and a directory with the unfinished marker; `install` still refuses it and names `adopt`.
2. Tests first for the plan over a scratch repository: a missing file is **create**; an existing seeded file is **kept**;
   an existing real directory is reused; an existing module-owned path, a file where a directory is planned, a directory
   where a file is planned, or a link anywhere on a planned path refuses the whole plan listing every conflict; a block
   for an existing file is **not filled** with its file and slot named.
3. Implement the state and the plan. The plan reads existing files through descriptors without following links and hashes
   them with no filters. The preview never prints the content of an existing file (the preview rule).
4. Hostile cases run through the real code path: a link planted between the check and the read, a huge existing file, a
   `.workbench` link, a path with control characters in the output.
**Verification:** the new tests; the installer root's `test_target*`, `test_preview*` and `test_install*` unchanged and
green; `git diff --check`.
**Evidence:** the one local commit, trailer `Plan: 2026-10-25-adopt-existing-repository#B`.

### Increment C — `wb adopt`

**Outcome:** the owner can adopt a scratch repository, and a failure part-way is recoverable.
**Dependencies:** B.
**Affected areas:** `workbench/install.py` or a new `workbench/adopt.py`, `workbench/cli.py`, `workbench/unfinished.py`,
`workbench/recover.py`, `workbench/rules.py` (the owner-run command list the harness deny rules are rendered from), tests
(new `test_adopt.py`, additions to `test_recover*` and to the tests of `rules`), and, only if it lists the owner-run
commands, `packages/workbench/claude/tests/test_claude_harness.py`.
**Steps:**
1. Tests first: the approval binds the digest of the plan including the kept hashes; a kept file changed between the
   preview and the write refuses and writes nothing; every existing file is byte-identical after a successful adopt; the
   manifest holds each kept seeded file with the hash of the bytes there and each created file with the bytes written;
   baselines and the store record are as `install`'s; `adopt` does not run `attach` and says so.
2. Implement the write path, reusing `install`'s order and exclusive creation for what is new, and the held-descriptor
   re-check for every kept file.
3. Fail it part-way (a write that stops) and run `recover`; it removes only what `adopt` created and never a kept file.
4. Refusal when standard input and output are not terminals.
5. Add `adopt` to the owner-run list in `workbench/rules.py`. Tests first: the rendered deny rules for a harness contain
   `adopt` in the `wb` spelling and the four interpreter spellings, `preview adopt` is not denied, and an agent-run
   `adopt` is refused by the command itself as well. Check whether the `claude` module's test lists the commands; if it
   does and must change, record that its shipped approval is now stale (the owner runs `release-approvals`).
**Verification:** the new tests; the installer root's suite; `git diff --check`.
**Evidence:** the one local commit, trailer `Plan: 2026-10-25-adopt-existing-repository#C`.

### Increment D — Security review

**Outcome:** an independent adversarial review of the adoption path has run and each finding is resolved.
**Dependencies:** C, and the owner's "start d".
**Affected areas:** `workbench/` and `tests/` files B and C changed, this plan's Review record and Result; nothing else.
**Steps:**
1. Run the `security-review` skill's method on B and C with the `security-reviewer` agent, starting from the cases in B
   step 4 and adding the boundaries the skill names: shell and subprocess arguments (none expected), path guards in both
   directions, links on any planned path, hostile `.git` and `.workbench` entries, huge or special files, the digest
   binding, the held-descriptor re-checks, the unfinished-write marker, and the harness deny list.
2. Treat every finding as untrusted. Reproduce it, add a regression test that fails before the fix, fix it in the file it
   belongs to, and have the fix attacked once more. A finding I reject is recorded with the evidence.
3. Record in this plan: what was checked and found sound (by test or by reading), each finding with its disposition, and
   the residual risk.
**Verification:** the regression tests; the installer root's suite; `git diff --check`.
**Evidence:** the one local commit of the fixes and tests (trailer `Plan: 2026-10-25-adopt-existing-repository#D`), with
the findings in the Result. If there are no code changes the commit holds the plan's record only.

### Increment E — An adopted project works with the other commands

**Outcome:** `check`, `acknowledge`, `upgrade` and `attach` behave on an adopted project, and the documentation says how
to adopt.
**Dependencies:** D.
**Affected areas:** `tests/` (new `test_adopt_lifecycle.py`), `docs/development.md`, `README.md`, and `workbench/` only if a
test shows a defect.
**Steps:**
1. Test first, on a scratch repository adopted with the nine first-party modules: `check` passes; `acknowledge` accepts the
   manifest; `upgrade` classifies each kept seeded file **skip** and offers the unfilled blocks as appends, and applying it
   fills them; `attach` leaves a harness file with equal bytes and refuses one with other content, naming it.
2. Where a test fails, classify it as a defect in B or C (fix there, as part of this commit with the failing test kept) or
   a gap in the spec (stop and tell the owner).
3. Document the command and the follow-up steps (`attach`, `upgrade`, `acknowledge`) in `docs/development.md` and the
   README.
**Verification:** the new tests; the full suite; the document checks.
**Evidence:** the one local commit, trailer `Plan: 2026-10-25-adopt-existing-repository#E`.

### Increment F — Adopt and attach this repository

**Outcome:** this repository is an installed project with its harness attached and its edit gate active.
**Dependencies:** E, the owner's explicit "start", and `wb approve` of the first-party packages on this machine.
**Affected areas:** `.workbench/` and the per-clone harness files (created by the owner's `wb adopt` and `wb attach`), this
plan's Result; possibly `tests/` and `docs/specs/repository-boundary.md` where a check meets `.workbench/` for the first
time.
**Steps:**
1. I run `wb preview adopt` on this repository and put the figures in the Result: files created, kept, not filled. The
   expected kept files are the six `diverged` seeded files of `tests/fixtures/self_hosting_dispositions.json`.
2. The owner runs `wb adopt` in a terminal and approves the preview. I do not run it.
3. Harness files: `attach` has no preview, so I find by reading the harness module's declared files and hashing what
   exists which planned paths already exist here (`CLAUDE.md` and `.claude/` files from the old template are untracked) and
   whether each holds exactly the planned bytes. A path with equal bytes may stay. **Every path that exists with other
   content must be resolved by the owner before `attach` runs** (moved aside, with its content kept elsewhere if it is
   wanted, or replaced by hand); keeping it is not an option, because `attach` refuses a differing file and writes
   nothing, and the edit gate would stay inactive. I change none of these files. I tell the owner the list and stop.
4. The owner runs `wb attach` for the Claude harness. If it prints `refused:` or `failed:` the increment stops there with
   the gate inactive and the Result says so; it is not complete. When it succeeds I confirm the local manifest
   `.workbench/local/harness.json` exists, run `wb check`, show that a gated edit is handled as the spec says, and run
   the full suite; any test that meets `.workbench/` or the new harness files for the first time is a finding to fix in
   this increment or to record.
5. I list the new tracked files and ask the owner whether to commit them; the commit is a separate decision. The harness
   files stay untracked and are never committed.
6. Record the outcome. `docs/references/README.md` stays absent unless the owner adds it (the disposition `absent`).
**Verification:** `wb check` passes; the edit gate is active; the full suite is green with no new skip; `git status` shows
only the adoption's files.
**Evidence:** the one local commit of the adoption files if the owner approves it, trailer
`Plan: 2026-10-25-adopt-existing-repository#F`, and the Result.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots; the document checks and `git diff --check` print nothing.
- Every existing file in a scratch repository is byte-identical after `adopt`, by hash, in the tests.
- `wb check` passes on this repository after the owner's `wb adopt`.
- Not verified, by design: `adopt` on a repository other than scratch fixtures and this one; a remote-runner job; a
  live check that a session follows the installed policy blocks once they are filled.

## Risks and sensitive actions

- **A new write path into a populated, possibly untrusted directory.** This is the riskiest class of change the workbench
  has (it was the reason `self-hosting` split this out). The mitigations are the existing target rules (no links, no git,
  identity re-checked), the preview binding the digest, exclusive creation for what is new, and no write to any existing
  file. **The roadmap candidate requires a security review, so Increment D is one,** run after C and before E, with the
  adversarial cases in B step 4 as the starting list.
- **An agent could run `wb adopt`.** The harness deny rules come from `workbench/rules.py`; C adds `adopt` there and
  tests it, and the command refuses a non-terminal itself. A Bash deny is best-effort, not a security boundary
  (`harness-modules.md`), so the terminal test is the real guard.
- **Installed but not gated.** Until `attach` runs on this repository the edit gate is not active, which is why F includes
  it and Completion criterion 7 requires it.
- **The first adoption meets `.workbench/` in a repository whose tests never had one.** Increment F exists to contain
  that; a test that fails there is recorded, not hidden.
- **The kept hash is a claim about bytes at one moment.** A later edit is the project's, and `acknowledge` handles it as it
  does for any seeded file.
- **Scope.** Six increments, with a stop after A. If the spec work in A shows the write path needs more than described,
  I stop and propose a second plan rather than growing this one.
- **Sensitive actions:** none are taken by me. `wb adopt`, `wb approve` and any commit or push are the owner's or need the
  owner's word.

## Review record

Round 1 of 3, `ask-codex review-plan`, 2026-10-25 (model `gpt-5.6-luna`, effort medium), outcome changes needed, three
findings. I edited the plan for each, and the owner decided R1-F1, R1-F2 and R1-F3 as applied.

- R1-F1 (blocker, Goal and the first draft's Increment E, now F): the plan barred `adopt` from attaching but never scheduled an attach, so the
  adopted repository would not be gated. Accepted: Increment F now includes the owner-run `wb attach`, with existing
  harness files resolved by the owner; Goal 3, Choice 5 and Completion criterion 7 say the gate is active only after it.
- R1-F2 (major, security review): the roadmap candidate requires one and the plan made it optional. Accepted with a
  correction: it is now Increment D, run on the owner's "start d". That is consistent with the repository rule that an
  independent review runs when the owner asks, because the owner's approval of this plan and the "start" are the ask;
  Choice 9 says so.
- R1-F3 (major, harness deny rules): a new owner-run command must be added to the neutral list the harness denies.
  Accepted after checking the code: the list is `workbench/rules.py`, with `trust-and-approval.md` and
  `harness-modules.md` enumerating the commands. C now changes `rules.py` and tests it, A updates both specs, and the
  possibility that a `claude` module test lists the commands (and so stales its shipped approval) is recorded.

Round 2 of 3, `ask-codex review-plan`, 2026-10-25 (same model and effort), outcome changes needed, two findings. I edited
the plan for each, and the owner decided R2-F1 and R2-F2 as applied. The review is not archived; one round remains.

- R2-F1 (major, Increment F steps 3 and 4): step 3 let the owner keep a conflicting harness file, but `attach` refuses a
  differing file and writes nothing, which would leave the gate inactive. Accepted: every conflicting path must be
  resolved before `attach`, only equal-byte files may stay, and step 4 stops with the increment incomplete if `attach`
  refuses or fails. I also corrected my own wording: `attach` has no preview, so I find the planned paths by reading and
  hashing.
- R2-F2 (minor, `Specs:` line): the plan changes `trust-and-approval` and `harness-modules`. Accepted: both are listed.

Increment D, security review of B and C, 2026-10-25 (`security-reviewer` agent, two rounds, scratch copies only, Python
3.15 on case-insensitive APFS). I reproduced each finding before acting on it.

- D-F1 (medium, `target.py` `_classify`): a `.WORKBENCH` directory passed the "no `.workbench` entry of any kind" check
  on a case-insensitive volume, so `adopt` planned into a directory the repository controls. Reproduced with a failing
  test; fixed by refusing any case variant of `.workbench`. Test: `test_a_workbench_spelled_in_another_case_is_refused`.
- D-F2 (low, `adoptplan.py` `kind_of`): `agents.md` or `Docs/` beside a planned `AGENTS.md` or `docs` made the preview
  say "create" and `adopt` fail half-way (nothing lost: creates are exclusive). Reproduced; fixed by treating a name that
  differs only in case or Unicode form as a conflict. Tests: the two `differs_only_in_case` tests. Trade-off: on a
  case-sensitive volume a repository with `Docs/` and no `docs/` is refused too; it fails closed.
- The second round attacked the fix (nested variants, Kelvin sign, `.GIT`, NFC/NFD, trailing dot and space, fullwidth)
  and found no bypass. Names a volume does not fold do not collide, so the preview passes them.
- Accepted, no code change (Low): a kept file edited after the last re-check leaves a manifest hash that reads as
  "edited"; the file is never overwritten. The hash is a claim about one moment.
- Accepted, no code change (Low, pre-existing): the best-effort deny patterns in `rules.py` do not match `./wb`,
  `env`-prefixed, path-qualified or `-I` spellings, for `install` as much as `adopt`. The guard that holds is the
  terminal check on stdin and stdout in `install.py`; it was not tested against a pty.
- Found sound, by test: links and special files at kept and planned paths; a link or swap of a kept file and of a
  planned directory after the re-check (exit 3, nothing written through it); `recover` with a kept file modified,
  removed, replaced by a link or a directory (refuses, marker stays), and with a colliding user directory (survives);
  escape characters in the target name; hard links, FIFOs, oversized files. By reading only: the digest covers kept
  hashes and sizes, `reuse-dir` against `create-dir` and `not_filled`; creates use `O_EXCL|O_NOFOLLOW` through held
  descriptors; reads are bounded; no kept file can be pinned as a helper.
- Not tested: sockets (path too long) and device nodes (`mknod` not permitted); volumes other than APFS.

## Deferred work

- Reconciling the text of each `diverged` seeded file with its seed (Choice 6 keeps them as they are).
- Adopting a directory with no `.git`, or a worktree or submodule.
- The `mempalace` live check, and the owner-only trust check with a live run of `security-reviewer` (earlier plans).
- The owner's: archiving `claude_project_template` and its mentions in `~/.claude` (`global-config-migration`).

## Result

Increments A to E are local commits (`6e96c08`, `6e1fbb0`, `59da8a2`, `cc85bbe`, `66c21bc`, `aa5a9ed`); F is the
commit that carries this text. Nothing is pushed.

**Increment F, 2026-10-25.**

- `wb preview adopt` on this repository, with the nine first-party modules: 71 create-dir, 5 reuse-dir, 55 create-file,
  6 keep-file, 3 store writes, 5 blocks not filled. The kept files are the six `diverged` seeded files:
  `AGENTS.md`, `docs/README.md`, `docs/plans/README.md`, `docs/decisions/README.md`, `docs/roadmaps/README.md`,
  `docs/specs/README.md`. The not-filled blocks are `docs-index` (code-work, groundwork) and `policy` (code-work,
  groundwork, mempalace); `wb upgrade` offers them as appends.
- The owner ran `wb adopt`: 127 paths created, 6 existing files kept, nothing committed, no harness attached.
- Harness files: only `CLAUDE.md` existed with other content (the old template's, 47 bytes; `attach` writes
  `@AGENTS.md\n`). The owner moved it aside, and `attach` then wrote 26 files and `.workbench/local/harness.json`.
  `attach` needed `--package packages/workbench` because the package was installed from a local directory.
- `wb check` first failed on `.claude/remote-runner.toml`, the old template's path. The owner moved it to
  `.workbench/remote-runner.toml`, which then failed because it declared no profile. A `full` profile running
  `python3 -B -W error tests/run_all.py` was added, and `wb check` passes.
- The edit gate is active. Its first refusal (before `wb` was on the owner's `PATH`) failed closed with
  `wb: command not found`; its second refused every edit until the owner ran `wb approve-plan` for this plan.
  Both are the behaviour the specs describe.
- One test met the new state: `tests/fixtures/self_hosting_dispositions.json` recorded `docs/references/README.md` as
  `absent`, but `adopt` creates it from the `groundwork` seed. It is now `identical`. The plan's step 6 expectation
  that the file stays absent did not hold; the deferred item below is therefore done.
- `docs/specs/installer-interface.md` no longer says `adopt` is proposed or unbuilt.
- Verification: `python3 -B -W error tests/run_all.py` is green, 4224 tests in 10 roots, with the same three skips as
  before (one in `tests`, two in `code-work`); `doccheck`, `refcheck` and `git diff --check` print nothing.

**Not verified:** `adopt` on a repository other than scratch fixtures and this one; a remote-runner job; a live check
that a session follows the installed policy blocks once they are filled (they are not filled yet).

**Next:** run `wb upgrade` to append the five unfilled blocks, which is a separate decision. The harness files stay
untracked and are never committed.
