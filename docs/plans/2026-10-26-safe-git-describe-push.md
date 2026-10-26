# Build `safe-git describe push` and close the push gap

Status: In Progress
Created: 2026-10-26
Candidate: none (the push gap between plans 2 and 3 of the split of `docs/specs/action-review.md` for `workbench-v1#action-review-engine`; it builds the facts side for a push only, and the candidate is complete only when the engine is built, so the plan that builds the engine names the candidate)
Specs: safe-git, action-review

## Goal

Give the action-review engine the facts it needs to review a `git push`, in the interface the accepted decision
`2026-10-25-describe-interface-for-action-review` requires: a read-only `wb run safe-git describe push ...` that takes
the arguments of the real `git push`, reports what that push would send and where, and changes nothing. Today
`push-check` answers part of this for a human (six narrow secret patterns, the changed paths, `ahead`), and "The push
gap" in `docs/specs/safe-git.md` lists the checks of the owner's approver for which the module has no counterpart.
Until they have one, a push stays with the approver and the cutover (plan 5) cannot retire that program.

The owner chose on 2026-10-26: add `describe push` (not an extension of `push-check` alone), and close the whole gap
in this plan, not only the checks that cause the most declines. `push-check` is not removed or changed in meaning; it
stays for the `push-changes` skill.

When the plan is done:

- `safe-git.md` states the grammar of the push arguments `describe push` accepts, its facts, error codes, caps and the
  counterpart of each of the approver's `git-push` checks, and the owner has read it;
- `wb run safe-git describe push ...` prints one JSON object in the shape of `describe commit` and `describe remove`,
  for a push of the current branch, from local refs and configuration only, and never contacts the remote;
- the facts cover every item listed under "The push gap": the push's flags and refspecs, the resolved target, the
  remote and its transport, the configuration that makes a push run a program, whether the tracking ref's reflog looks
  written by git, and the outgoing commit messages and diff, with the omission rule of `describe commit` for what does not fit;
- the repository is the same after every call, and no program the repository or the push configuration selects is
  started;
- a security pass has covered the new git shapes, the configuration reads and the argument parser, and its findings are
  fixed or reported;
- `describes` lists `push`, and the specs say "built" for what is built.

## Scope

- `docs/specs/safe-git.md` ("Describe" and "The push gap"), `docs/specs/action-review.md` where it names the gap, and
  `docs/development.md`.
- `packages/workbench/safe-git/helper/safe-git`: the `describe push` action, its argument parser, the new fixed git
  shapes and the reads they need, and the shared pieces of the builder (`build_description`, the caps and the omission
  rule) which it reuses unchanged.
- `packages/workbench/safe-git/module.json` (`describes` gains `push`) and the module's tests.
- `workbench/shipped_approvals/packages/`: every change under `packages/workbench/` changes the package tree hash, so
  each increment that edits the package adds the approval records the owner's `release-approvals` writes, and the commit
  includes them. This was a departure from the plan's affected areas in the previous plan; here it is stated.

## Non-goals

- The engine, the rule schema, the rubric, the log, the hook and the shadow period (plans 3 to 5). This plan produces
  facts and judges nothing; in particular it decides no check of the approver, it only supplies what the engine needs
  to make it.
- Any change to what `push-check` prints or refuses. It keeps its fields and its patterns.
- Running `git push`, contacting a remote, fetching, or writing any ref, file or configuration. `describe push` is
  local reads.
- Any change to `commit` or `remove`, or to the caps and codes already built for them.
- A wider secret scanner. The engine's own scan over the outgoing `diff` (plan 3, as for a commit) replaces the six
  patterns; this plan gives it the diff and does not extend `_RULES`.
- The per-command permission levels (the owner's ADR and plan `2026-10-26-command-permission-levels` in another
  session), and any `ask` level for `push-shared-branch`. Those may later use `describe push` as the preview; this plan
  neither waits for them nor depends on them.
- `remote-runner describe` (M16).
- The owner's own steps: `wb upgrade`, `wb acknowledge`, `release-approvals`. The agent does not run them.

## Assumptions and constraints

- **The design starts as the author's proposal.** The interface decision fixes the object shape, the types, the exit
  statuses and the rule that the engine runs only `describe <action>`. It does not fix the push facts. Increment A writes
  them into `safe-git.md` and stops for the owner to read before any code is written; if the owner changes the design,
  the later increments follow it. Building must not change the spec to fit the code without the owner.
- **The real command is `git push`, which this module does not run.** `describe push` therefore has no real command in
  the helper to share validation with. It takes the arguments after `git push` (`describe push [<flags>] [<remote>
  [<refspec>...]]`), accepts a fixed subset of flags and refspec forms, and refuses everything else with the `usage` code,
  so a push it does not understand is not approved by a fact it cannot give. The subset is set in A.
- **This departs from the accepted decision, and the plan does not settle it.** `2026-10-25-describe-interface-for-
  action-review` says `describe` runs "the real command's own validation code" (item 2) and that a push "uses
  `push-check`, extended" (item 6), and item 1 says the arguments are exactly those of the real command. The owner chose
  `describe push` on 2026-10-26, and `action-review.md` names it as an option, but an accepted decision is superseded
  and never edited, and a clarification note cannot override it. So Increment A drafts a new decision record, `Proposed`,
  that narrows items 1, 2 and 6 for a push, says why the restricted parser stands in for the real command's validation
  and why its grammar is safe, and the owner accepts it. Increment B does not start until then. Approving this plan is
  not that acceptance.
- **Standard library only**, Python through kit 1.
- **No new surface that runs a program.** The repository is refused first if it selects a program, as `commit` does. The
  push-specific configuration (credential helpers, a proxy, an askpass program, a receive-pack or vcs setting, an ssh
  variant, a remote's `pushurl` that is a command) is reported by name, never by value, and is also a refusal when it
  would run a program. Values of `remote.<name>.url` and `pushurl` are never printed: a URL can carry a credential, so only
  its scheme and a boolean for embedded credentials are facts.
- **Reads are fixed git shapes** added to the allowlist with literal arguments, the helper's scrubbed environment and
  `GIT_OPTIONAL_LOCKS=0`. The expected set is `config` reads of named keys, `ls-remote`-free ref reads (`for-each-ref`,
  `show-ref`, `rev-parse`, `reflog show` of a tracking ref) and the log and diff of the outgoing range that `push-check`
  already runs. A is the place that lists them; the security pass tries each.
- **The tracking ref is local and can be forged or stale.** The report states what the refs say; it does not claim the
  remote's state, so it cannot say whether a ref the push names exists on the remote or whether the push would succeed.
  A reflog is local and cannot show who wrote a ref, so the trust fact is a heuristic that only says the reflog looks
  written by git, and the spec tells the engine to treat it as untrusted evidence. This is a recorded limit, as for
  `push-check`.
- **The edit gate and the shipped approvals.** Each increment that edits the package is built and tested in a copy in
  the scratch directory and landed with one `cp`, then the owner runs `release-approvals`, as in the previous plan. Stray
  Finder files (`.DS_Store`) inside the package trees make that command refuse; the owner keeps Finder windows off the
  repository.
- **Self-hosting.** The source helper and declaration change while the installed copy does not until the owner runs
  `wb upgrade --package packages/workbench` (the previous plan needed one such upgrade).
- **Tests that run git need it**, and skip with a reason without it.
- **Each increment is one reviewed local commit** made with `wb run safe-git commit`, with the `Plan:` trailer and no
  attribution. Review is the `reviewer` agent. A second-model review happens only if the owner asks.
- Discovery: graphify: skipped, no discovery tooling installed. The scope is one helper and its tests, plus two specs;
  the helper's `command_push_check`, `scan_patch`, `repo_program_findings`, `build_description` and the caps were read
  for this plan, and so were the specs' lists of the approver's `git-push` checks.

## Completion criteria

1. `safe-git.md` holds the grammar, facts, error codes, caps and the counterpart of each `git-push` check of the
   approver, and before any code is built the owner has accepted the design (the stop after A) and a new decision record
   that narrows items 1, 2 and 6 of the accepted `describe` decision for a push.
2. For each error code of `describe push` there is a test showing `ok: false` and that code, and an unknown or
   unsupported argument gives `usage`. An unknown first argument and an uncoded refusal still exit 1 with no object.
3. The facts equal what a real `git push` of the same arguments asks for, tested against a bare local repository used as
   the remote: the refs it asks to update or delete and the outgoing commits equal those a real push to that remote
   sends. The facts make no claim that a ref exists on the remote or that the push would succeed. The test pushes only
   to a local path in a temporary directory.
4. Every flag of the accepted subset appears as a fact, and a force, a delete, a tag and an all-branches push are each
   distinguishable from a plain push. A push whose targets depend on what the remote holds (`--mirror`, `--follow-tags`,
   `push.followTags`, `remote.<name>.mirror`) is refused with a named code, not reported with a partial target list,
   and so is a remote with more than one effective push URL.
5. The configuration reads give only names, never values, and a remote URL with embedded credentials gives the boolean
   and the scheme, never the URL; a test finds neither the credential nor the URL in the object.
6. The repository is byte for byte the same after every case (files, index, refs, reflogs, hooks, configuration), and a
   repository or push configuration that selects a program never starts it (marker tests), for each program setting
   the approver names.
7. A value over a cap is omitted whole, named in `omitted`, with `truncated: true`; the outgoing `diff` obeys the cap and
   the budget of `describe commit`; no string is cut.
8. `describes` is `["remove","commit","push"]` and `wb run safe-git describe push` runs through the launcher, while
   `describe` of any other action is still refused.
9. The owner was asked whether to run the security pass; if yes, it ran, its findings are recorded and each is fixed
   with a test or reported to the owner; if no, the Result records that it was declined.
10. `python3 -B -W error tests/run_all.py`, `wb check`, `wb run code-work check`, `doccheck` and `refcheck` pass, and
    the specs say "built" and keep the limits.

## Increments

### Increment A — Specify `describe push`

**Outcome:** `docs/specs/safe-git.md` states, for `describe push`, the push arguments it accepts, its facts with types, its
error codes, its caps and the counterpart (engine, rubric or fact) of each of the approver's `git-push` checks. "The push
gap" says what is closed and what remains. The owner has read it.
**Dependencies:** none.
**Affected areas:** `docs/specs/safe-git.md` ("Describe", "The push gap", the table of the approver's checks),
`docs/specs/action-review.md` (the split's mention of the gap), a new `docs/decisions/2026-10-26-<topic>.md` and the
row in `docs/decisions/README.md`. Documents only.
**Steps:**
1. Read `push-check` and its tests, the list in "The push gap", and the `describe commit` facts, caps and omission rule
   that the new object follows.
2. Write the grammar: the accepted flags (for example force, force-with-lease, delete, tags, all, set-upstream,
   no-verify, dry-run, atomic), what a remote and a refspec may look like, and that anything else is `usage`.
   `--mirror` and `--follow-tags` are not accepted, because what they send depends on the remote's refs; they, the
   settings `push.followTags` and `remote.<name>.mirror`, and a remote with more than one effective push URL each give a
   named code that says the remote's state or endpoints are needed. Say how the engine's own reading of the command text relates to the flags the helper reports.
3. Write the facts, in order, with types: the flags as booleans; `remote`, `remote_configured`, `remote_scheme`,
   `remote_url_has_credentials` (both taken from the effective push URL, which is the one git reports for a push after
   `pushurl` and the rewrite rules, never the fetch URL, and never printed); `push_config_findings` (names only); `branch`, `default_branch`, the refspec
   facts, flat and separate so no dimension is lost: `push_updates` (one `<source>:<destination>` string for each update),
   `push_deletes` (the destinations deleted, whether by `--delete` or by an empty-source refspec) and `push_forced` (the
   destinations a force flag or a `+` applies to), all resolved from the refspecs and from `push.default`, `pushRemote`,
   `remote.<name>.push`, with no claim whether a ref exists on the remote;
   `base`, `ahead`, `tracking_ref_reflog_looks_git_written` (a heuristic, to be treated as untrusted evidence);
   `commit_messages`, `changed_paths`, `findings` (the rule names of `push-check`) and `diff`.
4. Write the error codes (reusing `usage`, `repository_unreadable` and `repo_selects_program`, and naming the new ones:
   no commit, detached HEAD, a branch name the helper does not read, no base, an unconfigured remote, an unsupported
   flag or refspec, a push configuration that selects a program), and the caps (those of `describe commit`, with the
   outgoing path list at 200).
5. Extend the table "Each check of the approver, and where it goes" with the `git-push` checks, and rewrite "The push
   gap" to say which are closed by this plan and what stays (the race between `describe` and the push; the remote's own
   state; a stale or forged tracking ref).
6. Run the document checks and ask the `reviewer` agent to read it for drift against the accepted decision.
7. Draft a decision record, `Proposed`, in `docs/decisions/` (the `draft-decision` skill): it narrows items 1, 2 and 6 of
   `2026-10-25-describe-interface-for-action-review` for a push, with the reason (git push is not a command of this
   module) and why the restricted grammar is safe, and the index row. The agent does not accept it.
8. Stop. The owner reads the design and the record, accepts the record (the owner's act) and says to go on, or changes
   either. B does not start before then.
**Verification:** `wb check`, `wb run code-work check`, `doccheck`, `refcheck`, `git diff --check`; every approver check
of `git-push` named in the spec appears in the table once.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-safe-git-describe-push#A`.

### Increment B — The `describe push` action, its parser and the scalar facts

**Outcome:** `wb run safe-git describe push` (called directly on the helper in tests) parses the push arguments,
validates the repository and the branch as `push-check` does, and prints the object with the flags, the remote and
branch facts, `base`, `ahead` and `truncated`. A refused call is an object with a code; the later facts are empty or null.
It is not yet in `describes`.
**Dependencies:** A, accepted by the owner.
**Affected areas:** `packages/workbench/safe-git/helper/safe-git` (a parser for the push arguments; a describer for
`push` registered beside `commit` and `remove`; the usage line), tests in
`packages/workbench/safe-git/tests/` (a new `test_safegit_describe_push.py`), `workbench/shipped_approvals/packages/`.
**Steps:**
1. Write failing tests: each accepted flag; a refspec and a remote; every refusal of the parser as `usage`; a detached
   HEAD, an unborn branch, a branch name the helper does not read, a repository that selects a program, and no base, each
   with its code; the object has the specified fields in order; the repository is unchanged afterwards.
2. Add the parser and the describer. Reuse `repo_program_findings`, the branch reading and the base resolution of
   `command_push_check` by calling them, not by copying; if they must be split out, `push-check`'s tests pass unchanged.
3. Build and test in the scratch copy; land with one `cp`; the owner runs `release-approvals`.
**Verification:** new tests fail first, then pass; the existing `push-check` and `describe` tests pass unchanged with the
same count; `python3 -B -W error tests/run_all.py`; `git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-safe-git-describe-push#B`.

### Increment C — The remote, its transport and the push configuration

**Outcome:** `remote_configured`, `remote_scheme`, `remote_url_has_credentials` and `push_config_findings` are facts; a
push configuration that selects a program is refused with its code; no URL or value is ever in the object.
**Dependencies:** B.
**Affected areas:** the helper (new fixed `config` read shapes; the reduction of a URL to a scheme and a boolean), the
new tests, `workbench/shipped_approvals/packages/`.
**Steps:**
1. Write failing tests: a configured and an unconfigured remote; each scheme (https, ssh, git, file, a bare path, an
   scp-like form, an unknown one); a URL with a user name and a password, with a token, and with only a user name;
   `pushurl` set and different from `url` in scheme and in credential presence (the facts follow the push URL), and a
   `pushInsteadOf` rewrite; each configuration the approver names (credential helper, proxy, askpass, receive-pack, vcs, ssh
   variant) found by name and, where it would run a program, refused; the credential and the URL appear nowhere in the
   object or the error message; a marker program started by none of these.
2. Add the shapes to the allowlist with fixed arguments, and the reduction. Read configuration values in the helper and
   print names and booleans only.
3. Land as in B.
**Verification:** as in B, plus the marker and no-leak tests named above.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-safe-git-describe-push#C`.

### Increment D — The push target

**Outcome:** `push_updates`, `push_deletes` and `push_forced` state which remote refs the push asks to update or delete,
from which source, and which are forced (and not whether they exist there), from the refspecs of the command and from `push.default`, `pushRemote` and `remote.<name>.push`; a push that depends on the
remote's own refs (`--mirror`, `--follow-tags`, `push.followTags`, `remote.<name>.mirror`) is refused with its code;
`default_branch` and the flags agree with it.
**Dependencies:** C.
**Affected areas:** the helper (the resolution; new fixed ref and config reads), the new tests,
`workbench/shipped_approvals/packages/`.
**Steps:**
1. Write failing tests against a bare local repository as the remote and a real `git push` to it in a temporary
   directory: a plain push, an explicit refspec, `HEAD:other`, a delete refspec, `--delete`, `--tags`, `--all`, a force flag and a `+` refspec, each of `push.default`'s values, `pushRemote`, and
   `remote.<name>.push`, an empty-source deletion (`:branch`), and two sources with one destination. For each, the refs
   the real push updated or deleted (read from its `--porcelain` output) equal the three lists, with the source and the
   force of each. A case that cannot be resolved from local data gives an empty list and a code, never a guess. Tests
   also give each refused form its code: `--mirror`, `--follow-tags`, `push.followTags`, `remote.<name>.mirror`, and a
   remote with two `pushurl` values.
2. Write the resolution. It reads local configuration and refs only.
3. Land as in B.
**Verification:** as in B; the equality tests against the real push pass, and no test pushes anywhere but a temporary
local directory.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-safe-git-describe-push#D`.

### Increment E — The outgoing commits, their trust and the diff

**Outcome:** `commit_messages`, `changed_paths`, `findings`, `tracking_ref_reflog_looks_git_written` and `diff` are facts, with the
caps and the omission rule of `describe commit`, and the object is complete or says it is not (`truncated`).
**Dependencies:** D.
**Affected areas:** the helper (the log of the outgoing range for messages, the reflog read of the tracking ref, the
outgoing diff built under the diff limits and budget of `describe commit`; `describes` gains `push` in `module.json`),
tests including `tests/test_safegit_module.py`, `workbench/shipped_approvals/packages/`.
**Steps:**
1. Write failing tests: the messages equal `git log` of the range, a merge commit, a range with no commits, a message
   with control characters or a long body, an outgoing diff at the cap and one byte over (omitted whole), binary and
   non-UTF-8 content as in `describe commit`, a secret pattern giving a rule name and no text, a tracking ref written by
   a fetch and one written by hand (the fact is a heuristic, and a test shows a forged reflog fools it, which the spec
   records), and the declaration test that `describes` is exactly `remove`,
   `commit`, `push`.
2. Add the reads and the builders. The diff reuses the existing text diff and budget; it never runs a filter, a text
   conversion or an external diff.
3. Declare `push` in `describes`. Land as in B.
**Verification:** as in B; `wb run safe-git describe push` through the launcher works against the source declaration in
a scratch project, and `describe` of another action is refused.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-safe-git-describe-push#E`.

### Increment F — Security pass and its fixes

**Outcome:** the owner has been asked whether to run a security review; if yes, the pass over `describe push` has run
and each finding is fixed with a test that failed first or reported to the owner; if no, that is recorded. The
Result records either. The increment always ends in one commit.
**Dependencies:** E.
**Affected areas:** the helper and its tests, `workbench/shipped_approvals/packages/` if fixes land; the plan's Result.
**Steps:**
1. Stop and ask the owner whether to run a security review (approval of this plan is not that answer). The
   `security-review` module is installed in this repository; if it were not, say so. On yes, use the
   `security-reviewer` agent: give it the new shapes, the argument parser, the URL and configuration reductions, the
   target resolution and the outgoing diff, and tell it to use scratch copies only. On no, skip to step 3.
2. Evaluate each finding as a review comment. For each one that holds, write the failing test, fix it, and land as in B.
3. Ask the `reviewer` agent to read the fixes (or the increment, if the pass was declined). Record the pass or the
   refusal, the findings, the fixes, what was found sound by test and what was not checked.
**Verification:** the new tests fail first, then pass; `python3 -B -W error tests/run_all.py`; `wb check`;
`git diff --check`.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-safe-git-describe-push#F`.

### Increment G — The specs say what is built

**Outcome:** `safe-git.md` ("Describe", "The push gap", "As built, and its limits"), `action-review.md` (the split), and
`docs/development.md` no longer say the push facts are not built, and the limits found are written down.
**Dependencies:** F.
**Affected areas:** those documents only; no file under `packages/workbench/` changes.
**Steps:**
1. List every mention of the push gap and of `describe push` as not built; change each to the built form or to what remains.
2. Record the limits found, the departures from A's text if any, and the owner's remaining steps (`wb upgrade`).
3. Run the document checks and the reviewer.
**Verification:** `wb check`, `wb run code-work check`, `doccheck`, `refcheck`, `git diff --check`; a search for the
phrases returns only the open limits.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-26-safe-git-describe-push#G`.

## Verification for the plan as a whole

`python3 -B -W error tests/run_all.py` (all tests), `wb check`, `wb run code-work check`, `doccheck` and `refcheck`
(`env PYTHONPATH=workbench python3 -B packages/workbench/groundwork/helper/{doccheck,refcheck}`), `git diff --check`, the
before and after repository comparison in every `describe push` test, and the equality tests against a real push to a
bare local repository.

## Risks and sensitive actions

- **Security-sensitive new surface.** `describe push` reads remote URLs and push configuration, which can hold
  credentials, and the outgoing diff, which can hold secrets. Mitigation: only names, schemes and booleans are printed;
  fixed shapes; the early refusal of a repository that selects a program; marker and no-leak tests; Increment F.
- **A fact that is wrong looks like an approval.** A wrongly resolved target or a missed force flag would let the engine
  approve a push that is not what it says. Mitigation: the equality tests against a real push, an unresolved case giving
  an empty list and a code rather than a guess, and the rule that the engine declines on `truncated`.
- **No real command to share validation with.** The parser is new code that must agree with what git accepts. A flag it
  does not know is `usage`, never a guess; the equality tests cover each accepted flag.
- **Self-hosting.** The source helper changes while the installed one does not; the owner upgrades. The agent runs no
  `wb upgrade`, `acknowledge`, `attach` or `install`.
- **Facts carry hostile text** (a commit message, a diff) to a future model call. This plan only produces them; the engine
  treats them as data (decision, item 4).
- **Overlap with the per-command permission levels** being specified in another session, which also names `push-check`
  and `push-shared-branch`. The two do not touch the same files; a conflict would show in `workbench/rules.py` and the
  approver coverage, which this plan does not edit.
- **Nothing is committed, pushed or deleted** except by the owner's word at each increment.

## Review record

Reviewed by the review engine through the `ask-codex` bridge (model `gpt-5.6-terra`, effort medium) on 2026-10-26, at the
owner's request: four rounds (the bound of 3, extended to 4 by the owner). Every finding was judged on the evidence and
applied.
- Round 1 (one blocker, three major): R1-F1, the plan's restricted parser departs from the accepted `describe` decision
  (items 2 and 6), which the plan had not recorded; R1-F2, a push's create-versus-update cannot be known without
  contacting the remote; R1-F3, the reflog "written by git" fact overstated what a forgeable reflog shows; R1-F4,
  approval of a plan was treated as consent to a security review.
- Round 2 (one major): R2-F1, superseding item 6 alone leaves items 1 and 2 in conflict, and a note cannot override an
  accepted decision, so a new record is required.
- Round 3 (two major): R3-F1, a list of target ref names loses the source, delete and force of each refspec; R3-F2, the
  scheme and credential facts must come from the effective push URL, not the fetch URL.
- Round 4 (two major): it said the round 1 to 3 fixes hold. R4-F1, `--mirror`, `--follow-tags` and the settings
  `push.followTags` and `remote.<name>.mirror` send what the remote's refs decide, so local facts cannot equal the push;
  they are now refused with a named code. R4-F2, git pushes to every configured push URL, so a remote with more than one
  is refused with a named code and a test.
All nine were applied to the plan. Round 4 was the last within the extended bound (the ceiling is 5), so the two fixes
of round 4 have not been read by the engine. Their detail belongs to the spec that Increment A writes, which the owner
reads. The review is not an approval; the plan stays `Proposed` for the owner.

## Deferred work

- The engine, the rule schema, the log, the shadow hook and cutover (plans 3 to 5).
- A wider secret scan than the six patterns, which belongs to the engine.
- Reading the remote's own state (`ls-remote`): it would contact the remote and is outside a local-only fact.
- `remote-runner describe submit` and `fetch` (after M16).
- Using `describe push` as the read-only preview for an `ask` level of `push-shared-branch`, if the owner accepts the
  per-command permission levels.

## Result

### Increment A — Specify `describe push`

Done, not yet committed at the time of writing. Documents only; nothing under `packages/workbench/` changed. Changed:
`docs/specs/safe-git.md` (a new section "`describe push`": the grammar, the range, the remote and configuration rules, the
git shapes it adds, the facts, nine new error codes, the caps, what stays with the approver, and the 14 `git-push` checks
of the approver each mapped to a fact), `docs/specs/action-review.md` (the push rows and the split), the new Proposed
record `docs/decisions/2026-10-26-describe-push-takes-the-push-arguments.md` and its row in `docs/decisions/README.md`.
It narrows items 1, 2, 3 and 6 of the accepted `describe` decision for a push only. The agent has not accepted it and
cannot. B does not start before the owner has read the spec and accepted the record.

Verification as run: `wb run code-work check` (51 plans), `doccheck`, `refcheck` and `git diff --check` clean. `wb check`
reports one problem until the commit: the decisions README points at the new record, which git does not track yet.
Nothing was built or run against Git; two attempts to probe Git behaviour in a scratch repository (`git remote get-url
--push --all`, `git config --list --show-scope -z`) were not run, because the one command was denied as a compound line.
Those behaviours are unverified and are settled by the tests of B to D against a real push to a local bare repository.

Review: the `reviewer` agent, two exchanges. The first found four blocking problems, all applied: B1, the range, `base` and
`ahead` described a different push whenever the source was not the current branch (the grammar now allows one update from
the current branch, or deletions only; `--all`, `--tags` and other sources are `usage`); B2, the diff could omit binary,
submodule and deleted content with `truncated` false (new facts `binary_paths` and `submodule_paths`, deleted paths in
`changed_paths`, and `facts_complete` requires both lists empty); B3, the record and the spec disagreed on wildcard
refspecs (now `remote_state_required` in both); B4, a configuration key with a subsection can carry a URL (named without
its subsection). Ten smaller points were applied or recorded as limits. The second found no blocking problem; its points
were applied: the raw shapes behind `submodule_paths` must not use `--ignore-submodules`, no `usage` message quotes an
argument, a non-empty `findings` declines (a secret added and removed inside the range), and several small
inconsistencies. Not checked by the reviewer: it ran nothing and could not read the approver.

Departures from the plan's wording, for the owner (the approved plan is not edited): the plan's criteria 2 and 4 and
Increments B to E still mention `--tags`, `--all`, the facts `tags` and `all_branches`, and `remote_configured`; the spec
drops them (`--tags` and `--all` are `usage`, and `remote_unconfigured` is an error, not a fact). Increment E also needs a
test with a changed gitlink and Increment C one with a URL passed as a remote argument. If the owner wants the plan to say
so, that is an edit beyond status, review record and result, and needs a new approval.

Open for the owner: the facts print the scheme of the push URL but not its host, so `destination_is_appropriate` sees only
the remote name; a host fact is deferred. Accepting the decision record is the owner's act.
