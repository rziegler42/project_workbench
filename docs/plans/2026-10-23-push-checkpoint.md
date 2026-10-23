# The shared-branch push checkpoint

Status: Approved
Created: 2026-10-23
Candidate: workbench-v1#push-checkpoint
Specs: code-work, safe-git, harness-modules

## Goal

`code-work.md` says a push to a shared branch is a checkpoint the owner decides, that the project declares its shared
branches under `.workbench/`, and that the credential scan comes before the push. Today none of that is built: the
checkpoint name `push-shared-branch` is declared and nothing reads the shared branches, nothing scans, and no skill
tells an agent the routine. The only thing in force is the floor: every harness with `permissions` already renders an
`ask` rule on `git push` (`rules.FLOOR_RULES`, the hard stop "publish or deploy").

When this plan is done:

- a project can declare shared branches in committed configuration, and `wb run code-work shared` reports the declared
  list (read-only, no git, no program);
- `wb run safe-git push-check` reports, read-only, the current branch, the default branch, what a push would send, and
  credential-looking lines in it, by file and rule and never by the matched text;
- a neutral skill, `push-changes`, tells the agent the routine: find out whether the branch is shared, run the check,
  report to the owner, wait for the owner's word, push only then, never force, never push on a commit's say-so;
- the specs say what is built and its limits, and the package's approvals are released by the owner.

## Scope

- A read-only `push-check` subcommand in `packages/workbench/safe-git/helper/safe-git`, with its git argument shapes
  and tests (increment A).
- A read-only `shared` subcommand in the `code-work` helper, the configuration file it reads, and tests (increment B).
- One neutral skill, `push-changes`, in `code-work`, and its tests (increment C).
- Spec text, the released approvals and the plan's Result (increment D).

## Non-goals

- A `push` subcommand. The agent pushes with `git push` and the harness asks, as it does now. The helper never pushes,
  fetches or writes anything.
- Lifting the floor. The floor asks on every `git push`, shared or not, and nothing may remove a hard stop
  (`trust-and-approval.md`). So the spec's "a push to any other branch is not a checkpoint" holds for the process and
  not for the harness: a non-shared push still prompts. See choice 4.
- A secret scanner of any strength. The scan is the owner's narrow pattern list, a guard against a mistake.
- Any effect of `delegate` (`delegated-approval`), and merging on the hosting side.
- A project-level setting that lowers a checkpoint (deferred by `2026-10-22-checkpoint-settings-and-caps`).
- Moving the commit helper or `remove`. They stay in `safe-git` unchanged.

## Assumptions and constraints

- The `code-work` helper contains no git code and starts no program (`safe-git.md`, acceptance criteria). So git
  work goes to `safe-git`, which already owns the guarded runner: a `git` found only in an absolute `PATH` entry
  outside the repository, a scrubbed environment, argument shapes, and a refusal when the repository selects a
  program to run.
- A module helper is a standalone script; modules do not import each other. The skill composes the two commands.
- `workbench/` and `tests/` hold only mechanism; `tests/test_boundary.py` must stay green. Nothing new goes there.
- Reading a diff can run a program a repository names (an external diff, a text conversion). The scan must switch both
  off and refuse a repository that selects one, as `commit` does.
- Everything the scan reads is data. Its output must carry no matched text, so a finding is not itself a leak.
- Editing the `code-work` or `safe-git` tree changes their tree hashes, so the shipped approvals go stale; the release
  is the owner's (`release-approvals`, run only on "Run it for me"; stale records removed only after a preview and
  "remove them").
- Discovery: graphify: skipped, not installed here; the scope was enumerated from the specs, `rules.py` and the
  `safe-git` helper.

### Choices (made by me; the owner may change any)

1. **Two commands, one skill.** `safe-git push-check` does the git-dependent work (branch, default branch, range,
   scan). `code-work shared` reads the declared list. The skill joins them. Alternative: put all of it in `code-work`
   and give that helper git code; rejected because it breaks the recorded rule that `code-work` starts no program
   and would duplicate the guarded runner.
2. **The shared set is the default branch plus the declared list, and the current file is authoritative.** The file is
   `.workbench/shared-branches.json`, `{"format": 1, "shared": ["name", ...]}`, read without following a link and
   bounded, duplicate keys refused. The default branch is always shared, so no edit can lower that. Removing a declared
   non-default branch does lower the process checkpoint for it; nothing compares the file with an earlier version, and
   building that would need the prior committed list from git. This departs from `code-work.md` ("Committed
   configuration may add shared branches and may not remove one"), which increment D rewrites, and the owner may
   instead ask for a monotonic mechanism. The harness stop does not move: the floor asks on every push (choice 4). It
   is not `.workbench/code-work.json`, which once held the attribution setting and is read by nothing; reusing the
   name would give a stale file a new meaning.
3. **The scan's patterns are the ones used by hand so far:** a PEM private-key header, an AWS access key id, a GitHub
   token (`ghp_`, `github_pat_`), an `sk-` key, a Slack token (`xoxb-`, `xoxp-`), a JWT-shaped string; and added file
   names `.env`, `*.pem`, `id_rsa`. A finding is `{path, line, rule}`: `line` is the line number in the new file for a
   content finding and `null` for a file-name finding. The range is `<base>..HEAD`, added lines only. **The base**
   is chosen from local refs only and the command never contacts the remote: `--base` if given; otherwise
   `refs/remotes/<remote>/<branch>` for the current branch if that ref exists; otherwise
   `refs/remotes/<remote>/<default branch>`; otherwise a refusal naming what was tried. The upstream setting is not
   read. The output names `remote`, `target` (the branch a push of HEAD would update, the current branch) and `base`,
   so the report says what is being compared. Choosing which branch to push is still the owner's word, not the
   command's.
4. **A non-shared push still prompts.** The floor stays. The skill says a non-shared push needs no scan or report
   but the harness will ask; the owner approves at the prompt as now. Changing that means changing the floor, which is
   the owner's separate decision and not this plan's.
5. **The rule the harness enforces is the floor's `ask` on `git push`.** This plan adds a test that the rendered Claude
   settings for an attached `code-work` still ask on `git push` and on a force push, rather than a second rule. No
   new rule is rendered.
6. **A skill is advice.** Nothing forces the agent to run the check. The `ask` is what stops a push.

## Completion criteria

1. `wb run safe-git push-check` prints one JSON line with `remote`, `branch`, `target`, `default_branch`, `base`, `ahead`, `changed_paths`
   and `findings` (each `{path, line, rule}`, `line` null for a file-name finding); it runs only the git shapes added for it, with external diff and text conversion off; it refuses
   a repository that selects a program, an unborn branch, a detached HEAD, a base it cannot resolve from local refs (it names what it tried), and an
   argument it does not allow; it never contacts the remote; it prints no matched text; it changes nothing.
2. `wb run code-work shared` prints `{"format": 1, "shared": [...]}` from `.workbench/shared-branches.json`; an absent
   file is an empty list; a link, a malformed file, a duplicate key, a wrong type or an oversize file is refused; it
   starts no program and contains no git code.
3. `code-work` ships a neutral skill `push-changes` that states: push only on the owner's word, a commit is not a word;
   whether the branch is shared is `default_branch` or a name in `shared`; run `push-check` first and report its
   findings and the commits to be sent; stop on any finding until the owner decides; never force, never push a
   branch the owner did not name, never change the remote; the harness's prompt is not the owner's word.
4. For the Claude layout the installer plans `.claude/skills/push-changes/SKILL.md` and the rendered settings still
   ask on `git push` and on each force form.
5. The specs say what is built and its limits; `code-work.md` no longer lists `push-checkpoint` as not built; the
   full suite, `doccheck`, `refcheck` and `git diff --check` pass; the shipped approvals are released by the owner
   and the suite then runs with no Claude skip.

## Increments

### Increment A — `push-check` in `safe-git`

**Outcome:** a read-only command that says what a push would send and whether it looks like it carries a credential.
**Dependencies:** none.
**Affected areas:** `packages/workbench/safe-git/helper/safe-git` (new subcommand, new git shapes);
`packages/workbench/safe-git/module.json` (`push-check` in `arguments`); a new test file in
`packages/workbench/safe-git/tests/`; the module test that lists the arguments.
**Steps:**
1. Tests first, with the existing `support_git` fixtures: the shapes `rev-parse --abbrev-ref HEAD`,
   `rev-parse --verify -q refs/remotes/<remote>/<branch>`, `symbolic-ref --short refs/remotes/<remote>/HEAD`,
   `rev-list --count <base>..HEAD` and `diff --no-ext-diff --no-textconv -U0 <base>..HEAD` pass `git_shape_ok` and nothing wider does (a leading dash in a ref, `..` twice, a
   `@{` form, an option after the range are refused); a clean range gives `findings: []`; one planted key of each
   pattern gives one finding by path, line and rule with the matched text absent from the output; a removed line
   with a key gives none; a file named `.env` added gives a finding with `line` null; the base is the current branch's remote-tracking ref when
   it exists, else the default branch's, else a refusal, and an explicit `--base` wins; no network is used (a remote
   that points nowhere is never contacted); an unborn branch, a detached HEAD, an unknown
   base and a repository that selects a program are refused with the reason; a configured external diff driver and a
   text conversion do not run (a marker file is not created); output is bounded and a large range reports a
   truncation and not a hang. Run them and see them fail.
2. Add the shapes and `push-check` (`--remote` default `origin`, `--base` optional, validated like a branch ref). Read
   the diff once with a byte cap and a timeout. Print one JSON line; on a refusal write `refused: <reason>` to
   standard error and exit 1, as `commit` does.
3. Run the new tests, the module's tests and the boundary test.
**Verification:** `env PYTHONPATH=. python3 -B -W error -m unittest discover -s packages/workbench/safe-git/tests -t
packages/workbench/safe-git/tests`; `python3 -B -W error -m unittest tests.test_boundary`.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-push-checkpoint#A`.

### Increment B — `shared` in `code-work`

**Outcome:** the declared shared branches are readable by an agent without git.
**Dependencies:** none.
**Affected areas:** `packages/workbench/code-work/helper/code-work` (new subcommand);
`packages/workbench/code-work/module.json` (`shared` in `arguments`); a new test file in
`packages/workbench/code-work/tests/`; the module tests that list the arguments and the shipped files.
**Steps:**
1. Tests first: absent file gives an empty list; a valid file gives its names in file order; a name that is not a
   branch name, a duplicate name, more than 64 names, a name over 200 bytes, a link, a directory, a file over 8 KiB,
   a duplicate JSON key, `format` other than 1 and an extra key are each refused; the helper still imports no
   subprocess and contains no `git` command (the existing test for that is extended to cover the new code). Run
   them and see them fail.
2. Implement `shared` with the helper's existing safe reader and strict JSON reader where they exist; otherwise the
   same checks written in the helper.
3. Run the new tests and the module's tests.
**Verification:** `env PYTHONPATH=. python3 -B -W error -m unittest discover -s packages/workbench/code-work/tests -t
packages/workbench/code-work/tests`; the boundary test.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-push-checkpoint#B`.

### Increment C — The `push-changes` skill

**Outcome:** an agent has the push routine as a skill, and the harness still asks before any push.
**Dependencies:** A, B.
**Affected areas:** `packages/workbench/code-work/harness/neutral/skills/push-changes/SKILL.md` (new);
`packages/workbench/code-work/tests/test_codework_skills.py` and `test_codework_module.py` (the tree lists, the
allowed `wb` commands); a new test that plans the Claude settings.
**Steps:**
1. Tests first: the reader accepts the new skill with front matter `name` and `description` only; the Claude layout
   plans `.claude/skills/push-changes/SKILL.md`; the text carries the phrases of criterion 3; at most 60 lines; the
   only commands named are the allowed `wb` commands, now including `wb run safe-git push-check` and `wb run
   code-work shared`, each exactly and in backticks; `git push` appears at most as the plain command the owner
   approved, and no force form, no remote change and no other raw git; the existing word scans still pass. A test
   renders the Claude settings for an attached `code-work` with `safe-git` and asserts the `ask` rules for `git
   push` and each force form are present. Run them and see them fail where new.
2. Write the skill: stop unless the owner asked for a push; run `wb run code-work shared` and `wb run safe-git
   push-check`; shared means the branch is `default_branch` or in `shared`; report the commits to be sent, the
   changed paths and every finding; with a finding or a refusal, stop; otherwise wait for the owner's word and then
   run the push of that branch to that remote; report the result; for a non-shared branch, say the harness will ask.
3. Run the new tests and the module's tests.
**Verification:** the module tests; the boundary test.
**Evidence:** the one local commit, trailer `Plan: 2026-10-23-push-checkpoint#C`.

### Increment D — Spec and record

**Outcome:** the specs say what is built, the approvals are released, and the plan records it.
**Dependencies:** C.
**Affected areas:** `docs/specs/code-work.md` ("Push", "Declaration", "As built", "Not built"), `docs/specs/safe-git.md`
(purpose and non-goals, declaration table, a "Push check" section, "As built"), `docs/specs/harness-modules.md` only
if it names the push as unbuilt, the package approvals (owner-run), this plan's Result.
**Steps:**
1. Edit the specs: the subcommands, the file and its schema, the patterns, what the scan does not catch, the floor
   asking on every push (choice 4), and that the skill is advice. Rewrite the `code-work.md` "Push" rule on committed configuration to match choice 2. Fix the safe-git non-goal so it
   no longer says "no other git operation" without naming the read-only checks.
2. Run the full suite. If it reports the approvals stale, stop and ask the owner to run `release-approvals`; preview
   any stale record and delete it only after "remove them". Run the suite again.
3. Run `doccheck`, `refcheck` and `git diff --check`; search the docs for a statement that the push checkpoint is not
   built.
4. Fill the Result, including that no live session was used. Set `Status: Completed` only after every criterion has its
   evidence.
**Verification:** the full suite with no Claude skip; the document checks print nothing.
**Evidence:** the one local commit (specs, plan, refreshed approval records), trailer
`Plan: 2026-10-23-push-checkpoint#D`.

## Verification for the plan as a whole

- `python3 -B -W error tests/run_all.py` is green in all roots with no Claude skip; `git diff --check`, `doccheck` and
  `refcheck` print nothing.
- The scan and the shared list are shown by tests against scratch repositories with planted fake keys; no real
  secret is used and no remote is contacted.
- Global items this plan will let `global-config-migration` retire, none yet: the instruction in `~/.claude/CLAUDE.md`
  to check for secrets before a push and to ask before one stays until a recorded run shows a project behaves the
  same without it.
- A live check is possible and not planned: attach `code-work` and `safe-git` in a scratch project, ask for a push and
  see the check, the report and the prompt. Until the owner runs it, live behaviour is unverified.

## Risks and sensitive actions

- **The scan is heuristic.** It misses encoded, split or unlisted secrets and flags false positives. It is a guard
  against a mistake, not a control, and the owner decides.
- **Reading a diff in an untrusted repository.** External diff drivers, text conversion, hooks and filters can run
  programs; the command switches the first two off, refuses a repository that selects a program, runs only listed
  shapes in a scrubbed environment and bounds time and bytes. Branch and remote names are validated before they reach
  git. A security pass on the new surface is part of review if the owner asks.
- **Output as a leak.** A finding carries path, line and rule only. A path can itself name a secret; paths are
  printed as the repository holds them and the owner sees them.
- **A skill is advice.** Nothing makes the agent run the check; the floor's `ask` is the only stop.
- **Shared-branch configuration is committed and authoritative.** A pulled edit that adds a branch only widens the
  checkpoint. One that removes a declared non-default branch narrows the process checkpoint for it (choice 2); the
  default branch stays shared, and the floor still asks on every push. The file is a difference `wb acknowledge` lists
  where the installer tracks it, so a pulled edit is seen; that is not verified for this file and the plan does not
  rely on it.
- **The package trees change.** Approvals go stale; the release is the owner's and stale records are deleted only
  after a preview and "remove them".
- No push, no install into a project, no secret and no deletion beyond stale approval records. The plan's tests plant
  fake keys in scratch repositories only.

## Review record

Round 1 of 3, 2026-10-23, `ask-codex review-plan`, model `gpt-5.6-luna`, effort medium (asked for by the owner).
Outcome: changes needed; two major findings and one minor, all applied before approval.

- R1-F1 applied. The base of the range was undefined. Choice 3 now gives the algorithm (local refs only, no network),
  the output names `remote`, `target` and `base`, and increment A tests it.
- R1-F2 applied, and the plan's claim was wrong. Nothing compares the file with an earlier version, so removing a
  declared non-default branch narrows the process checkpoint. Choice 2 now says so and makes the current file
  authoritative; the departure from the spec is rewritten in increment D; the risk text is corrected. The owner may
  instead ask for a monotonic mechanism.
- R1-F3 applied. A file-name finding has `line` null; the contract and the tests say so.

Nothing rejected. Left for the owner: choice 2 (authoritative file or a monotonic mechanism), whether to approve, and
whether to ask for a further round.

## Deferred work

- Lifting the floor's `ask` for a non-shared push, which needs the owner's decision on the floor.
- A monotonic shared-branch list, so that removing a declared branch has no effect. It needs the earlier committed
  list from git, more git shapes in `safe-git`, and rules for a first commit, a rebase and a missing remote branch
  (choice 2).
- A project-level lowering of a checkpoint, and `delegate` (`delegated-approval`).
- A stronger scanner, or the owner's own pattern list in configuration.
- A `push` subcommand with the check built in, if the owner wants one command.
- A live check in a scratch project.

## Result

Not started.
