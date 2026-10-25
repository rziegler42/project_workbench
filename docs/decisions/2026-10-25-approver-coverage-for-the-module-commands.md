# How the approver comes to review the module commands

Status: Accepted by the owner on 2026-10-25 (option 1a)
Date: 2026-10-25

## Context

The owner's approver is a `PermissionRequest` hook program at the user level. It reviews a command that an `ask` rule prompted for,
logs a verdict, and for two delegated rules can allow the command. The accepted decision
`2026-10-25-module-commands-and-the-approver` chose that the owner adds global `ask` entries for the four module spellings
(`wb run safe-git commit`, `wb run safe-git remove`, `wb run remote-runner submit` and `fetch`) and that the module commit is not
delegated. That decision settled what raises a prompt. It did not settle how the approver comes to review the prompt, because the
plan `2026-10-25-approver-coverage-for-module-spellings` assumed that this was a data edit of the approver's rules and rubric. It
is not (the inventory spec, M1 and F-A1).

What was measured, on a scratch copy of the program, calling its matching functions only (Increment B of the plan
`2026-10-25-approver-program-and-the-module-spellings`):

- None of the four module spellings, nor `wb run safe-git push-check`, matches any rule. The spellings are constants of the
  program, and a command whose raw text starts with none of them is never read against a rule.
- A rule for a tool outside the program's fixed list is refused. So is a malformed rule file, a file with a missing key, and a
  file naming an unknown collector. A refused file makes the matching functions raise for every command that begins with a listed
  spelling and tokenizes, covered or not. A bad or missing configuration file or rules directory has the same effect.
- By reading, not by a run: the hook's entry point swallows that error, so no verdict, no outcome row and no decision is made, and
  the normal prompt is expected. The owner's mode is `delegate`, so under such an error the delegated commit and archive no longer
  auto-allow. That is a loss of convenience and of the log, not a bypass.
- By reading: the approver's review of a commit or a removal calls the global `claude-workflow` program as a library (to
  validate paths and messages and to read the repository). The program is the subject of move M14. Adding spellings does not end
  that dependence.

The constraints that bear on the choice are two. A project guarantees a floor, and does not write the user level
(`2026-10-24-project-guarantees-a-floor`). And the enforcement point stays in the owner's configuration; the action-review engine
returns verdicts as data and authorizes nothing by itself (`2026-10-22-model-calls-go-through-vendor-bridges`, items 6 to 8). No
plan exists for that engine (`action-review-engine`).

Whether a global `PermissionRequest` hook fires on a prompt that a project `ask` raised, in an interactive session, is still
untested. It matters only for the `git push` prompt (move M9), which the project renders itself.

## Decision

The owner chose **option 1a** (the narrow change to the approver program) and accepted the record on 2026-10-25. The choices are
set out below as they were written. Nothing here is built, and nothing at the user level changes by writing this record. The
owner makes the change to the program; the agent prepares and tests a patch on a scratch copy under its own plan, which does not
exist yet and needs the owner's approval.

1. **The owner changes the approver program** so that it recognises the module spellings. The agent cannot write the user level,
   so the owner makes the change, or has it prepared as a patch to review. The list of what changes (read, not run; line numbers of the
   program as it stood on 2026-10-25): the spelling lists and the map from spelling to tool (43 to 59); the table of installed
   tools (38 to 39); the supported-tools list (60); `split_command` (100), which must consume a multi-word prefix such as
   `wb run safe-git` and map it to a tool; the installed-helper check (`resolve_invocation`, from 449), which reads a spelling's last
   word as a path under the home directory; the collectors that load the global program (`load_helper` 387, `collect_commit` 867,
   `collect_remove` 947); the outcome hooks, which follow the matching (`process_outcome` 2225); new rule files for the four
   spellings; and the hook entries per spelling in the settings file. `DELEGABLE` (77) stays as it is. The approver then reviews
   the module commands on the owner's machine; a project without the owner's settings gets no review; the owner makes the change.
   Two variants:
   - **1a, narrow.** The collectors keep calling the global `claude-workflow` program. M1 stage 1 no longer blocks M9 and M16 once the owner
     adds the `ask` entries (M9 still needs the F-B1 test, and M16 the change to the `remote-runner` program, F-C6). M14 stays
     blocked while the approver depends on the program.
   - **1b, wide.** The collectors for commit and removal are rewritten to get their facts from the module that owns the action
     (`wb run safe-git`), so M14 can follow. This is the work item 7 of `2026-10-22-model-calls-go-through-vendor-bridges` leaves
     open, and it is close to the engine's own work.
2. **The owner waits, and the coverage is built into `action-review-engine`.** The approver is redesigned there (M1 stage 2); the
   engine is built under its own plan, which does not exist, by whoever the owner plans it with, and the owner places the
   enforcement point.
   Until it exists the module commands prompt on the owner's machine through the global `ask` entries and the approver sees and
   reviews none of them; once it exists it reviews them. A project without the owner's settings gets no review. M9, M14 and M16 stay blocked on the engine, which has no plan.
3. **The owner keeps the global helpers and accepts that M9, M14 and M16 stay blocked.** The global `claude-workflow`,
   `remote-runner` and `ask-codex` programs, their `ask` entries and the approver stay as they are. The module commands remain
   available and prompt where the owner's `ask` entries say, without the approver's review (it sees none of them). The owner makes
   no change. A project without the owner's settings gets the workbench's floor and nothing more.

Whichever is chosen, the global `ask` entries of the accepted decision are needed: under 1 they raise the prompt the approver
reviews, under 2 they raise it for the engine to review once it exists, and under 3 they are the only protection for the module commands on the owner's machine.

## Alternatives considered

- **Add the spellings to the rules and the rubric only.** Rejected by Increment B: a rule for a tool outside the program's fixed
  list is refused, and the spellings are matched before any rule is read.
- **Make the matching rule-driven, with the spelling lists in a data file.** This is a variant of option 1, a larger change to the
  program. It would let the owner add a spelling without editing code, and it would put the safety of the list into a file whose
  one typo, as measured, disables the approver for every command with a listed spelling. The owner may want it as a
  separate choice; it is listed here, not ranked.
- **A project-rendered hook that does the approver's work.** Rejected by `2026-10-22-model-calls-go-through-vendor-bridges` and
  `2026-10-24-project-guarantees-a-floor`: the enforcement point stays in the owner's configuration.
- **Delegate the module commit.** Not part of this record. The accepted decision chose not to delegate, and `DELEGABLE` stays a
  code constant that widening needs its own decision for.

## Consequences

- **Option 1a:** a smaller change than 1b (unmeasured) that gets the approver's review onto the module commands on the owner's machine. It leaves the
  approver reading the repository through the global `claude-workflow` program, so that program stays installed until 1b or the
  engine. The owner edits a security-relevant program that they maintain, and the edit needs its own review and tests; a mistake in
  the new spellings or rule files, as measured, can silence the review and the commit delegation for every command. A teammate or
  a clone on another machine gets no review from it.
- **Option 1b:** the same, plus a rewrite of the approver's fact collection. It ends the dependence on the global program and
  makes M14 possible, at the cost of a much larger change to the program, in the place where the engine is meant to go.
- **Option 2:** no change to the approver now. The module commands run on the owner's
  machine without the approver's review, behind the `ask` prompt, for as long as the engine has no plan. The engine would need
  its own plan, the interface to the module that owns the action (open in the vendor-bridges decision), and a security pass.
- **Option 3:** nothing changes. M9, M14 and M16 and the removal of the global programs stay open, and so do the findings that
  depend on them (the commit agent and the guard's committer mode accept only the global spelling). The loss is that the
  workbench's own commands are not the ones the owner uses.
- **Every option:** a project without the owner's global settings gets no approver review of the module commands. That follows
  from the floor and from the approver living in the owner's configuration.
- **Every option:** the F-B1 test (a global hook firing on a project `ask` in an interactive session) is still owed before M9 can
  be called safe, and the owner makes it.

## Verification

Read and run, on 2026-10-25, at commit `a31c426` of this repository, Python 3.15.0, Darwin 25.6.0. The approver program
(SHA-256 `94ac5e8cd05473081ff0004130592cdb94e0bbd19199777574c599a23cca2b0b`), its configuration, rubric, schema and eight rule
files were copied into a scratch directory and hashed identical to the originals, before and after. The matching functions were
called there; no model call and no real run of the hook. The control lines matched, the module lines did not, and the refused-file
results above were reproduced by an independent security reviewer with 15 variants of its own (advice from a model, not a
verdict). The results and the plan's Increment B are in the inventory spec (M1, F-A1) and in the plan's Result. Not run: the
hook's entry point, the outcome hooks, the installed-helper check, a patched program, and any interactive prompt. The statements
marked "by reading" were not run.

## Related files and decisions

- `docs/specs/global-config-inventory.md` (M1, M9, M14, M16, F-A1, F-A7, F-B1, F-B2)
- `docs/plans/2026-10-25-approver-program-and-the-module-spellings.md`, `docs/plans/2026-10-25-approver-coverage-for-module-spellings.md`
- `2026-10-25-module-commands-and-the-approver`, `2026-10-24-project-guarantees-a-floor`,
  `2026-10-22-model-calls-go-through-vendor-bridges`
