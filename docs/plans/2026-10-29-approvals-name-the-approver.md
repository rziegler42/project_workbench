# Approvals name the approver by git identity

Status: Proposed
Created: 2026-10-29
Candidate: workbench-v1#approval-identity
Specs: trust-and-approval, terms, installer-interface

## Goal

Build `2026-10-29-approvals-name-the-approver-by-git-identity` (accepted 2026-10-29). Today every approval record holds an
`approver` that is the operating-system account name, or the word `owner` when that lookup fails. After this plan an approval made by
`wb approve`, `wb pin`, `wb approve-plan` or `wb delegate-approve-plan` holds the person's git identity as `Name <email>`, read the
way the decision fixes, and a `via` that says how it was authorized. The word `owner` is no longer written as an approver. A command
refuses, and says how to set the identity, when it cannot read a valid one. The specs say so.

## Scope

- A new reader of the identity, `workbench/identity.py`, that runs `git config --global --get user.name` and `user.email` exactly as
  decision 2 says, checks the result against the grammar of decision 4, and returns the stored text `Name <email>`, or refuses.
- Plan approvals: the record format rises from 2 to 3 and gains `via`; the approver limit rises to 256; `approve-plan` records
  `terminal`, `ask` or `none`, and `delegate-approve-plan` records `delegated`; the command prints the approval as a sentence.
- Module and package approvals and pins: the record format of each rises by one, gains `via` and the larger limit; `approve` and
  `pin` record `terminal` or `none`, and print the approval as a sentence (the forms are under Increment C).
- The pins that the installer and `wb acknowledge` write are not approvals by a person: they keep the role text they have
  (`pinplan.py` passes its own `who`; `acknowledge.py` writes `workbench acknowledge`) and carry no `via`. In the new pin format `via`
  is optional, present for a pin made by `wb pin` and absent for these two writers.
- Removal of `approve.approver_name()` and its fallback to `owner`.
- The specs: `trust-and-approval.md` (the approver, the record fields and formats), `terms.md` (the word "approver") and
  `installer-interface.md` (what the commands print).

## Non-goals

- Who may approve. Identity is an unverified label; the decision says this is not decided here.
- A setting that fixes an identity, or a read of the project's git configuration.
- Raising the format of the shipped approvals. They are written by `release-approvals` with the fixed approver `workbench-release`
  and stay at the record format they have (see Assumptions). The one re-release this plan makes (Increment B) is forced by an edit to
  a package test, and writes records of the same kind.
- The convention in the decisions and plans READMEs and the seeded `AGENTS.md`. That is module text, and it goes with the policy and
  module-asks plan.
- Rewriting an approval already made. Entries written before the change are read as they are and stay as history.
- Any change under `packages/` other than the one test named in Increment B. If another package test fails because of this plan,
  stop and ask.

## Assumptions and constraints

- The decision is accepted and this plan builds what it says, including the grammar (decision 4), the exact invocation (decision 2)
  and the four values of `via` (decision 3). The plan does not reopen them.
- Which git to run is fixed by the plan and not by the caller's `PATH`: the first of `/usr/bin/git`, `/usr/local/bin/git` and
  `/opt/homebrew/bin/git` that is a regular, executable file. A run with no terminal (`ask`, `none`, delegated) happens in an
  agent's environment, and a `git` placed first on that `PATH` must not be able to name the approver. The existing helper
  `fetch.git_executable()` uses the caller's `PATH` and is not reused for this. If none of the three exists the command refuses.
- A format change keeps the old reader: a file at the earlier format is read, and the next write replaces the file at the new format.
  In a plan approvals file at format 3 an entry written before the change has no `via` and keeps its old approver text; an entry
  written after it has both. `via` is read as absent for an old entry and is never invented.
- The shipped records keep format 1 (module and package approvals) and carry no `via`: `workbench-release` is a role, and `terminal`
  would be false for it. The readers accept format 1 and the new format for module and package approvals. This departs from the
  wording of decision 4, "each record format that holds it is raised one version", in one place, and the owner's approval of this plan
  is the approval of that choice.
- The approval is bound to hashes. The approver is provenance, and no check reads it, so changing it cannot change what is approved.
- `workbench/` is not under `packages/`, so editing it does not make a shipped approval stale. A package is: the whole run of
  `tests/run_all.py` found, after Increment B's code was written, that `packages/workbench/code-work/tests/test_codework_module.py`
  runs `approve-plan` in-process and so reads the account's real git identity; editing that test makes the shipped approvals of the
  `code-work` module and of the `workbench` package stale until the owner runs `wb release-approvals`, and until then the command gate
  refuses every shell command.
- On this machine the owner's global git configuration holds neither `user.name` nor `user.email`; the identity is set only in this
  repository's `.git/config`, which the decision never reads. Until the owner sets the two values with `git config --global`,
  `approve-plan` and `approve` refuse here. That is the owner's act and is a precondition of the owner's trial.
- The test for the include directive is real: it runs git in a temporary home with an `include` in the global file and checks the
  identity is not read through it. Tests need a `git` binary and skip, saying so, where there is none.

## Completion criteria

1. `identity.read()` returns `Name <email>` for a valid global configuration and refuses, with a message that says how to set it,
   for a missing, empty or ungrammatical name or email. The tests cover the grammar's edges and the hostile cases of Increment A.
2. A plan, a module, a package and a pin approval made after the change hold the identity and a `via`, and the commands print the
   sentence. The four records at their earlier formats are still read.
3. No code writes `owner` as an approver; `approver_name` does not exist; the whole `tests` root passes.
4. The specs describe the records, the identity and `via`, and `wb check` and `wb run code-work check` report no problems.
5. `wb verify packages/workbench` runs with no refusal, so no shipped approval is stale, and `git status` shows no file changed
   outside `workbench/`, `tests/` and `docs/`, the one package test of Increment B, and the shipped approvals the owner's release
   rewrote for it.

## Increments

### Increment A — Read the identity

**Outcome:** `workbench/identity.py` reads and checks the git identity exactly as decisions 2 and 4 say, with tests, and nothing calls
it yet.
**Dependencies:** none.
**Affected areas:** `workbench/identity.py` (new), `tests/test_identity.py` (new).
**Steps:**
1. Write the tests first, against a temporary home and a real `git`: a valid identity; a name or an email that is missing or empty;
   the length edges (name 1 and 100, email 3 and 100, stored text 210); `<` or `>` in either; two `@` or none, and nothing on a side of
   it; a space, a tab and a control character in the email; a line or paragraph separator, a control, a format, a surrogate, a
   private-use and an unassigned character in the name; a name that changes under NFC normalization and is stored normalized.
2. Write the hostile cases: a project `.git/config` that sets a different identity (not read, with the working directory never the
   project); `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_COUNT`, `GIT_CONFIG_PARAMETERS` and `GIT_DIR` set in the caller's environment (ignored);
   an `include` in the global file (not followed, so an identity that exists only in the included file is missing); a `git` earlier on
   the caller's `PATH` (not run); a global file that is a symbolic link or unreadable (refused, not read around).
3. See them fail, then write `identity.py`: a fixed list of git locations; the account's home from the account database; an
   environment built from nothing (`HOME`, a fixed `PATH`, `GIT_CONFIG_NOSYSTEM=1`, `LC_ALL=C`); two argument-list runs with no
   shell, a timeout, a bounded output and the home as the working directory; the grammar; the comparison key (the lowercased email);
   an error class whose text names the value and the rule and says how to set the value.
4. Run the new tests and the `tests` root.
**Verification:** the new tests fail before the code and pass after; the `tests` root passes; the boundary test passes (the module
names no harness); `wb check` reports no problems.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-approvals-name-the-approver#A`.

**Checkpoint after A.** The module runs a subprocess on a path it chooses, reads a configuration file and takes text from it into a
record. Ask the owner whether to run a security review before B.

### Increment B — Plan approvals

**Outcome:** `approve-plan` and `delegate-approve-plan` write the identity and a `via`, at format 3, and print one sentence.
**Dependencies:** Increment A.
**Affected areas:** `workbench/planapprovals.py`, `workbench/delegation.py`, `workbench/identity.py` (a `parse` that is the inverse of
`check`), `tests/support.py` (a helper that fixes the identity), `tests/test_planapprovals.py`, `tests/test_delegation.py`,
`tests/test_approve_levels.py`, `tests/test_gate_hook.py`, `tests/test_identity.py`, and the one package test
`packages/workbench/code-work/tests/test_codework_module.py` with the shipped approvals the owner's release rewrites for it.
**Steps:**
1. Write the tests first: a format 2 file is read and its entries come back as they were; the next write gives format 3, keeps the old
   entries without `via`, and adds the new one with `approver` and `via`; the limit is 256 for `approver` and the format 3 entry
   needs `via` in the four values; an old entry in a format 3 file may lack `via`, a new one may not; when `via` is present, `delegated` requires a valid `delegate`
   object and `terminal`, `ask` and `none` forbid one, and both mismatches are refused on read and on write; an old entry with a
   `delegate` and no `via` is still read; the delegated entry carries
   `delegate` and `via` `delegated`; a missing identity refuses before anything is written and before a prompt is shown; the printed
   line. Today it is `approved: <plan> (region <hash>)`, or `already approved: ...` for a repeat. The new forms add a tail after the
   region: ` by <Name <email>>` for `terminal`, ` by <Name <email>> (ask)` for `ask`, ` by <Name <email>> (no gate)` for `none`, and
   ` by <Name <email>> delegated to <provider> (<model>)` for a delegated approval (no model: the parenthesis is left out). A
   repeat names the approver and `via` on file, in the same forms, and an old entry without `via` is shown by its approver text
   alone. The tests fix the exact text for all four, and Increment D copies it into `installer-interface.md`.
2. See them fail. Then raise `FORMAT` to 3 and `FORMATS` to `(1, 2, 3)`, raise the limit, add `via` to the entry, read the identity
   once at the start of the command, record `terminal` when both streams are terminals and the level otherwise, and print the sentence.
3. Replace the two calls of `approve.approver_name()` here and the one in `delegation.py`. Read the identity after the level or the
   setting is checked and before any helper runs, so a missing identity refuses early; at a terminal, before anything is shown.
4. Run the test files and the `tests` root.
5. Run `tests/run_all.py`. Make the one package test (`Install.test_a_plan_is_approved_and_read_back_through_the_installed_module`)
   supply a fixed identity by patching `identity.read` around its `run` helper, as the other tests now do, without changing what it
   asserts. It is the only package test found to fail; if another does, stop and ask.
6. The edit makes the shipped approvals stale and the command gate refuses shell commands. Stop and ask the owner to run
   `wb release-approvals`. Then run `wb verify packages/workbench` and read the paths that changed under
   `workbench/shipped_approvals/`.
7. The release leaves the stale records of the earlier release on disk and reports them. List them with
   `wb run safe-git remove -- <path>...`, show the list to the owner, and remove them only with the owner's approval of that list
   (`--confirm`, and `--recursive` for a directory).
**Verification:** the new and the existing plan-approval and delegation tests pass; `tests/run_all.py` passes in every root;
`wb verify packages/workbench` runs with no refusal; `wb check` and `wb run code-work check` report no problems; `git status` shows
only the paths named under Affected areas, the new shipped records and the removed stale ones.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-approvals-name-the-approver#B`.

### Increment C — Module and package approvals and pins

**Outcome:** `approve` and `pin` write the identity and a `via`; the old record formats are still read; `approver_name` is gone.
**Dependencies:** Increment B.
**Affected areas:** `workbench/approvals.py`, `workbench/approve.py`, `workbench/pins.py`, `workbench/pinplan.py`,
`workbench/acknowledge.py`, `workbench/firstparty.py`, `tests/test_approvals.py`, `tests/test_approve.py`,
`tests/test_approve_pin_levels.py`, `tests/test_pins.py`, `tests/test_firstparty.py`, `tests/test_install_pins.py`,
`tests/test_upgrade_pins.py`, `tests/test_acknowledge_pins.py`, `tests/test_recover_pins.py`.
**Steps:**
1. Write the tests first: a format 1 record is read and checked as before, and its approver and time are kept when the same thing is
   approved again; a format 2 record has `via` and the larger limit; `approve` at a terminal writes `terminal` and at the level `none`
   writes `none`; the same for `pin` and its `pinned_by`; the missing identity refuses before the typed hash is asked for; the
   release still writes `workbench-release` at format 1 with no `via`, and two releases give identical files.
2. Write the output tests, from the current output read first (`approve.py` prints `approved <kind> <subject>` and, for a repeat,
   `already approved <kind> <subject> (by <approver> on <time>); the earlier record is kept`; the pin command prints
   `pinned <name> -> <path> (sha256 <hash>)`). The new forms are: `approved <kind> <subject> by <Name <email>>` for `terminal` and
   `... by <Name <email>> (no gate)` for `none`; the repeat names the approver on file, whatever its form; the pin line gains
   `by <Name <email>>` in the same two forms. The tests fix the exact text, and the text in `installer-interface.md` (Increment D)
   is copied from them.
3. Write the pin-migration tests: a format 1 pin file is read; `install`, `upgrade`, `add` and `acknowledge` read it and write
   the new format; a pin they write keeps its role text and has no `via`; a pin made by `wb pin` has both; a file holding both kinds
   round-trips; the installed and moved pins of the existing tests are unchanged in what they pin.
4. See them fail. Then add the new format to `approvals.py` and `pins.py` (reading both, `via` optional in a pin), let the release
   writer keep the old one, pass the identity and the `via` from `approve.run` and the pin command, and leave `pinplan.py` and
   `acknowledge.py` writing their role text without `via`.
5. Delete `approve.approver_name()` and its `owner` fallback; search the tree for the name and for the literal `"owner"` as an
   approver, and for any other caller.
6. Run the test files, the `tests` root and `wb verify packages/workbench`.
**Verification:** the tests pass; the `tests` root passes; the search for `approver_name` is empty; `wb verify packages/workbench`
runs with no refusal; `wb check` reports no problems.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-approvals-name-the-approver#C`.

### Increment D — The specs

**Outcome:** the specs say what is built.
**Dependencies:** Increment C.
**Affected areas:** `docs/specs/trust-and-approval.md`, `docs/specs/terms.md`, `docs/specs/installer-interface.md`.
**Steps:**
1. In `trust-and-approval.md`, replace the paragraph "Approver" (the operating-system account name) with the identity: the exact
   reading, the grammar, the comparison key, the limit, `via`, and that it is an attribution label and grants nothing. Update the
   field lists and the format numbers of the module, package and plan approval records and the pin record, and say that records at
   the earlier formats are read as history and that the shipped records keep the role `workbench-release`.
2. In `terms.md`, say in "approver" that it is recorded as `Name <email>` and how the way of authorization is recorded.
3. In `installer-interface.md`, show the sentence that `approve`, `pin`, `approve-plan` and `delegate-approve-plan` print.
4. Date the changes and state what was run: the commit, the tests and what was not run (a trial with no identity set on the owner's
   own machine, which is the owner's).
**Verification:** a search of the specs for the operating-system account wording and for "falls back" to `owner` comes back empty
in these three files; `wb check` and `wb run code-work check` report no problems; only these three files changed.
**Evidence:** the one local commit, with the trailer `Plan: 2026-10-29-approvals-name-the-approver#D`.

## Verification for the plan as a whole

- The whole `tests` root passes after the last increment, and `wb verify packages/workbench` runs with no refusal.
- `git status` shows no file changed outside `workbench/`, `tests/` and `docs/`.
- A read-only reviewer pass of each increment's diff, and the owner's read of each diff, before the commit is accepted.
- The owner's own trial, not run by the agent: `wb approve-plan` on a throwaway plan shows the owner's `Name <email>`, and with the
  global identity unset the command refuses with the instruction. The agent does not run `wb approve-plan`.

## Risks and sensitive actions

- The identity reader runs a subprocess and reads a file named by the account's home. Its inputs are a hostile `PATH`, a hostile
  environment, a hostile project configuration and a hostile global file. Increment A tests each, and a checkpoint offers a
  security review after it.
- The email goes into the guarded store and, later, into tracked status lines. The decision records this. A contributor with a
  personal address adds it to tracked text; the plan makes no change to that and the README convention is later work.
- An approval file is replaced whole. A format change must not lose an entry; Increment B tests that an old entry survives the
  rewrite, byte for byte in its fields.
- The departure from decision 4 for shipped records is stated under Assumptions. If the owner prefers the shipped records raised
  too, that is a different plan, because it needs a release and the owner's read of every shipped record.
- Editing `workbench/` leaves shipped approvals as they are. Editing the package test in Increment B does not, and shipping with
  the workbench counts as approval, so the release the owner runs is a trust act: the owner reads what changed in the shipped records
  (the `code-work` module and the `workbench` package, hashes and nothing else) before the commit. No other package is touched.
- A stale shipped approval stops every shell command at the command gate until the owner releases it. The package edit and the
  release are therefore made back to back, and the commit waits for the release.
- The deletion of stale records is the owner's decision, made on the list the helper prints.

## Review record

Plan review by Codex through the `ask-codex` bridge (model `gpt-5.6-terra`), rounds 3 of 3, the bound. Outcome: four findings, all
applied; the third round's finding was applied after the last round, so no round has read the final text.

- **Applied (major, round 1).** The pin migration listed one writer of pins. `pinplan.py` (installer pins) and `acknowledge.py`
  (moved pins) write pins too. They keep their role text and carry no `via`, which is optional in the new pin format; their
  tests are in Increment C.
- **Applied (major, round 1).** Increment C gave no output contract for `approve` and `pin`. It now names the current lines, the new
  forms and tests that fix the text.
- **Applied (major, round 2).** Increment B gave only the delegated sentence. It now fixes the line for terminal, ask, none and
  delegated approvals and for a repeat, and Increment D copies those forms into the interface spec.
- **Applied (major, round 3).** Nothing tied `via` to the `delegate` object. `delegated` now requires a valid `delegate`, the other
  three forbid one, and old entries without `via` are still read.
- **Not asked for.** A fourth round: the bound is 3. The owner may extend it, or read the last change and decide.

## Deferred work

- The convention in the decisions and plans READMEs, and the `AGENTS.md` wording that names the approver: the policy and module-asks
  plan.
- An identity set once in the personal settings, if the global git identity proves unstable (the decision's alternative).
- Who may approve: a separate decision.

## Result

**Increment A is done and committed (`6f2e957`, `67e4d1a`, `d3b0539`); Increment B is done and committed (`3aae9c5`); Increment C is
done and awaits the owner's word to commit; D is not started.**

### Increment A

- **Done.** `workbench/identity.py` reads and checks the git identity as decisions 2 and 4 say: two argument-list runs of
  `git config --global --get`, no shell, the account's home from the account database as the working directory, an environment of
  exactly `HOME`, a fixed `PATH` (`/usr/bin:/bin:/usr/sbin:/sbin`), `GIT_CONFIG_NOSYSTEM=1` and `LC_ALL=C`; git is one of three fixed
  files; a symbolic link at `~/.gitconfig` or `~/.config/git/config` is refused; the grammar, NFC, the comparison key (the lowercased
  email) and a refusal that says how to set the value. `tests/test_identity.py` holds 31 tests. Nothing calls the module yet.
- **Two choices of mine.** A name of nothing but blanks is refused (not in the grammar; it names nobody). Git is accepted when the
  fixed path is a link, because Homebrew's is one; the plan's "regular, executable file" did not say.
- **Verification as run.** The new tests failed with the module absent (import error) and pass with it (31 tests, OK). A mutation
  that passed the caller's environment through made two tests fail, so the environment tests bite. The whole `run_all.py` ran 5,960
  tests in 12 roots, OK; it ran with the first 28 tests of the file, and the 3 added after the review were run alone (31, OK).
  `tests/test_boundary.py` passes (19 tests); `wb check` reports no problems. The test that git ignores an `include` ran against the
  real git, Apple Git 2.54.0, and passed, so the decision's documented-behaviour claim was tested here.
- **Review.** One read-only reviewer pass: no blocking finding. Applied: an exact environment set and `PATH` value in the
  invocation test; tests of `account_home` with the account database patched, including its refusals; a test for the XDG symlink; a
  header note that the output is bounded only after it is read and that only Unix is supported. Not applied: the 210-character check
  cannot trigger (the maximum is 203), and is kept as a guard; the reviewer's concern that the macOS `/usr/bin/git` shim without the
  developer tools might exit 1 and be reported as a missing value was not tested here.
- **Not checked.** A symlinked parent such as `~/.config` is not refused, only the file. A person who keeps their dotfiles as links
  will see the symbolic-link refusal; the owner's `~/.gitconfig` is a regular file.
- **Committed as `6f2e957`.** The owner asked for the security review; it ran after that commit.

### Increment A, follow-up after the security review

- **Security review (2026-10-29).** The `security-reviewer` agent ran a copy of the module against real git (Apple Git 2.54.0, Python
  3.15.0) in temporary homes. Held: includes and `includeIf` not followed, the project's and `~/.git/config` not read, a `git`
  earlier on the caller's `PATH` not run, controls, NUL, CRLF and invalid UTF-8 refused, no hostile character reflected in a message.
  Found, all low or by its rating medium in a narrow case: unbounded memory from endless output (3.6 GB in 3 s); exit 1 with a
  message reported as a missing value; the symbolic-link check does not see a link at `~/.config` or at home and cannot close a
  check-to-read swap; Homebrew's git path is user-writable; Unicode data drifts by Python version; the grammar admits invisible-only
  names, names padded with spaces, lookalike brackets and long combining runs.
- **Applied (code, tests first).** A bounded read that kills the child at 4,096 bytes of output, 1,024 of messages or the timeout;
  "missing" only for exit 1 with no output and no message, otherwise "could not read" with git's message escaped and cut to 40
  characters; six new tests, of which four failed before the change; header notes for the limits. 37 tests in the file pass.
- **Not applied.** Owner and permission checks on the config files and the git path: they stop only an attacker who can plant a
  link but not write the file, and a root-owner rule would refuse Homebrew's git.
- **The grammar note, approved by the owner on 2026-10-29.** A clarification note on the accepted decision: a name must hold a
  letter, number, punctuation mark or symbol that shows (not a Hangul filler, the Braille blank, a Khmer inherent vowel or the
  grapheme joiner), and neither begins nor ends with a blank. Lookalikes and combining runs are left. It replaced my earlier rule
  that refused a name of only blanks. Four tests for it, 15 sub-cases failing before the code; 41 tests in the file pass.
- **Verification as run.** `tests/test_identity.py`, 37 tests, OK; the whole `run_all.py`, 5,969 tests in 12 roots, OK; `wb check` and
  `wb run code-work check` report no problems.

### Increment B

- **Done.** `workbench/planapprovals.py`: format 3 (`FORMATS` 1 to 3); `via` of `terminal`, `ask`, `none` or `delegated`; `delegated`
  exactly when `delegate` is present, for an entry that has a `via`; the approver limit 256 in format 3 and 64 before; a new entry's
  approver must parse as `Name <email>` on read and on write (`identity.parse`, new); `add` refuses an entry with no `via`; an old
  entry, including a legacy delegated one, is read as it is and never given a `via`. `approve-plan` records `terminal` or the level
  and `delegate-approve-plan` records `delegated`. The identity is read once, after the level or the setting is checked and before
  any helper runs (at a terminal, before anything is shown). The line ends ` by X`, ` by X (ask)`, ` by X (no gate)` or
  ` by X delegated to P (M)`; a repeat names the approver and `via` on file; an old entry shows its approver alone. The delegated
  line is now `approved: <plan> by X delegated to P (M), N of M rounds`, which changed from `(delegated, N of M rounds)`.
  `workbench/delegation.py` and the tests follow; `tests/support.py` has `fixed_identity`.
- **Found by the whole suite, and the amendment.** One package test, `Install.test_a_plan_is_approved_and_read_back_through_the_installed_module`
  in `packages/workbench/code-work/tests/test_codework_module.py`, ran `approve-plan` in-process and so read the account's real
  identity. It was the only failure of 5,997 tests. The plan was amended and the owner approved it again. The test now patches
  `identity.read` around its `run` helper; what it asserts is unchanged. Run with no git at all it still passes, so it supplies its
  own identity. It was run as its own root: 42 tests, OK.
- **The release.** The edit made the shipped approvals stale and the command gate refused commands, and a second edit was refused
  after the first (the gate had locked on the first). The owner ran `wb release-approvals` twice. The records now shipped for it:
  the `workbench/code-work` module record (`e4759edf…`, tree `fc84faaf…`) and the `workbench` package record (`79ebdf2e…`), both
  `workbench-release`, format 1, no `via`; only the `code-work` tree hash differs from before. The owner approved the two new records
  on 2026-10-29. The owner approved removing the four stale records the releases left (the two old tracked ones and the two from the
  first release), and they were removed with `wb run safe-git remove --recursive --confirm`. `wb verify packages/workbench` runs
  with no refusal.
- **Owner's global identity.** On this machine the global git configuration held neither value; the owner set both on 2026-10-29. Until
  then these commands refuse here.
- **Verification as run.** `test_planapprovals` 51, `test_delegation` 91, `test_approve_levels` 39, `test_gate_hook` 72 and
  `test_identity` 45 pass; a mutation that removed the `via` requirement and the via and delegate agreement made 8 tests fail. The whole
  `run_all.py`, run on the final tree after the release: 6,002 tests in 12 roots, OK. `wb check` and `wb run code-work check` report no
  problems.
- **Review.** One read-only reviewer pass: no blocking finding. Applied: the identity is read early, before any helper runs, in both
  commands (the reviewer found it read late), with tests that it is read once at that point, that a missing identity at `none` and
  in a delegated run writes and logs nothing and runs no helper, and that the level or the setting is refused before the identity.
  Not applied: a test of a rewrite of a legacy delegated entry through the file (covered by the parse and serialize round trip).
- **Not done.** The owner's own trial of `wb approve-plan` with the real identity, which the agent does not run. Increment C removes
  the last callers of `approve.approver_name`, which `approve` and `pin` still use.

### Increment C

- **Done.** `workbench/approvals.py`: a record is written at format 2 exactly when it has a `via` (`terminal` or `none`), with the
  approver as `Name <email>` (at most 256 characters, parsed by `identity.parse`); a format 1 record is read and checked as before;
  the release passes no `via`, so it still writes format 1 with `workbench-release`, byte for byte the same twice, and no shipped
  record changed. `workbench/pins.py`: format 2 is written and format 1 read; `via` is optional, present for a pin made by `wb pin`
  (with an identity as `pinned_by`, up to 256 characters) and absent for the installer's and `acknowledge`'s pins, which keep their
  role text and the 64-character limit; `via` is refused in a format 1 file. `workbench/approve.py` and `pins.run` read the identity
  first (before a download, a request, a prompt or a read of the helper), record `terminal` or `none`, and print ` by X` or
  ` by X (no gate)`; a repeat names the approver on file. `approve.approver_name`, its `owner` fallback and the `pwd` import are gone;
  nothing calls it. No source file writes the literal `owner` as an approver (the remaining hits are the declaration key `owner` and
  tests that use it as role text for a pin).
- **A mistake of mine, and a rule.** `workbench/pins.py` is code that the live edit and command gates load. I edited it in an order
  that left `FORMAT = 2` while the reader still required the file's format to equal `FORMAT`, so the gate refused every further edit,
  including the one that would repair it. I did not route around the refusal. The owner ran `git checkout -- workbench/pins.py`, which
  discarded only those 14 lines, and I redid the change so that every intermediate state still read the format 1 file and
  `FORMAT = 2` was the last edit. Rule for the rest of this plan: a parser or format that the gates load changes in an order that never
  leaves the stored file unreadable, or in one write.
- **Tests, first written after the code in part.** `tests/support.py` has `CHILD`, a stub that runs the command in a child process
  with the identity fixed (or missing), used by `test_approve.py` and `test_pins.py` so no test reads the machine's identity. New and
  changed: `test_approvals.py` 50 (a `ViaTest` class and format 2 parse cases), `test_approve.py` 55 (the old account-name tests
  replaced), `test_pins.py` 38 (format 1 read, format 2 written, `via` rules), `test_approve_pin_levels.py` 33 (the level `none`
  records `none`, a missing identity writes and logs nothing).
- **Verification as run.** The whole `run_all.py`: 6,022 tests in 12 roots, OK (it ran before the last small edits; the four edited
  files were run again after them and pass). A mutation that forced `via` to always read `terminal` made 2 tests fail.
  `wb verify packages/workbench` runs with no refusal (no package file changed, so no release); `wb check` and
  `wb run code-work check` report no problems.
- **Review.** One read-only reviewer pass: no blocking finding. Applied: `test_approve.py` uses the shared `support.CHILD` instead of its
  own copy; the `pins.py` docstring example shows the new `pinned_by`. Not applied, with reasons: reading stored identities more
  leniently (the grammar uses the Python version's Unicode tables, so a name written under newer tables could make an older Python
  refuse a pins file, which the gates load; rare, since the owner's name is ASCII, and fixing it would also change the reader of
  Increment B; it is a known limit for the owner to weigh); the gate now imports `identity` and with it `subprocess`, `selectors`
  and `pwd` (no import cycle; the gate runs).
- **For Increment D to cover.** `trust-and-approval.md` lines 392, 397, 500, 695 and 831 and the approval record formats; and
  `docs/development.md` line 258 ("the account name from the operating system's user database").
- **Not done.** The owner's own trial with the real identity.
