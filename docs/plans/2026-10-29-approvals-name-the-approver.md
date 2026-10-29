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
- Shipped approvals. They are written by `release-approvals` with the fixed approver `workbench-release` and stay at the record
  format they have (see Assumptions); no re-release is made and nothing under `workbench/shipped_approvals/` changes.
- The convention in the decisions and plans READMEs and the seeded `AGENTS.md`. That is module text, and it goes with the policy and
  module-asks plan.
- Rewriting an approval already made. Entries written before the change are read as they are and stay as history.
- Any change under `packages/`. If a package test fails because of this plan, stop and ask.

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
- `workbench/` is not under `packages/`, so editing it does not make a shipped approval stale.
- The test for the include directive is real: it runs git in a temporary home with an `include` in the global file and checks the
  identity is not read through it. Tests need a `git` binary and skip, saying so, where there is none.

## Completion criteria

1. `identity.read()` returns `Name <email>` for a valid global configuration and refuses, with a message that says how to set it,
   for a missing, empty or ungrammatical name or email. The tests cover the grammar's edges and the hostile cases of Increment A.
2. A plan, a module, a package and a pin approval made after the change hold the identity and a `via`, and the commands print the
   sentence. The four records at their earlier formats are still read.
3. No code writes `owner` as an approver; `approver_name` does not exist; the whole `tests` root passes.
4. The specs describe the records, the identity and `via`, and `wb check` and `wb run code-work check` report no problems.
5. `wb verify packages/workbench` runs with no refusal, so no shipped approval went stale, and `git status` shows no file changed
   outside `workbench/`, `tests/` and `docs/`.

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
**Affected areas:** `workbench/planapprovals.py`, `workbench/delegation.py`, `tests/test_planapprovals.py`,
`tests/test_delegation.py`.
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
3. Replace the two calls of `approve.approver_name()` here and the one in `delegation.py`.
4. Run the test files and the `tests` root.
**Verification:** the new and the existing plan-approval and delegation tests pass; the `tests` root passes; `wb check` and
`wb run code-work check` report no problems.
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
- Editing `workbench/` leaves shipped approvals as they are, so no re-release is needed. If a check says otherwise, stop and ask.

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

Empty until work starts.
