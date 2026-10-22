# The installer records and gates plan approval; the process module's pinned helper computes the hashed region

Status: Accepted by the owner on 2026-10-22
Date: 2026-10-22

## Context

`trust-and-approval.md` says a plan approval binds a hash of the plan's hashed region, kept per project in the
guarded store, and that the process module names the sections excluded from it. Nothing records one yet: approval
is the owner's statement in session. Three accepted rules bound the design:

- The installer knows nothing of plans; the plan check lives in the helper `code-work` ships
  (`2026-10-22-plan-check-in-the-shipped-helper`).
- A module command is agent-safe by design: `wb run` runs a pinned helper for anyone who can call it
  (`2026-10-21-module-code-lives-in-modules`, `module-boundary.md`).
- The guarded store is written only by owner-run commands that a harness denies to the agent
  (`2026-10-19-guarded-store`).

## Decision

1. **The installer owns the record and the gate.** It adds two commands: `approve-plan` (owner-run, terminal only,
   denied to the agent) writes a plan approval record into the guarded store, and `plan-status` (read-only,
   agent-safe) reports whether a plan's current state matches one.
2. **The process module's pinned helper owns what the hashed region is.** A `process` module declares an `approval`
   command (a command of its own and the argument that selects the subcommand). The helper reads the plan, applies
   the module's section rules and reports the region hash and the names of the unhashed sections as one bounded
   JSON object. The installer reads no plan and holds no section name.
3. **The command is run only as `wb run` runs a command.** The module is installed and approved, its declaration
   hash equals the manifest's and the helper is pinned and its bytes unchanged (the tree hash is not compared at run
   time, as for `wb run`). The installer treats the output as data.
4. **The record binds four things:** the plan's path relative to the root, the region hash, the process module's
   declaration hash and the helper's pinned hash. A change in any of them makes an old approval `changed since
   approval`. A new approval adds an entry; the first record of an identical approval is kept.
5. **Every approval is the owner's for now.** Delegated approval waits for a `peer-review` provider and a later
   decision about its record.
6. **The gate is a command and a rule.** Nothing here stops an agent that does not ask `plan-status`.

The formats are in `docs/specs/trust-and-approval.md`, "Plan approval records".

## Alternatives considered

- **A parser for the plan's sections in the installer, with the section names read from the declaration.** One
  reader for the installer, but the installer would know the plan format, against the accepted plan-check decision,
  and a second reader of fences and quotations would need a parity test. Rejected.
- **A `code-work` command that also writes the record.** No installer change, but a module command is agent-safe,
  so an agent could approve its own plan, and the harness cannot deny a command per module. Rejected.
- **A `Status: Approved` line as the approval.** Rejected by `trust-and-approval.md`: a committed line is never an
  approval.
- **A record keyed by the path alone, replaced on re-approval.** Simpler to read, but it would lose the history of
  what was approved and break "the first record is kept". Rejected.

## Consequences

- The plan format can change with the module without an installer release; an edit of the helper or of the
  declaration invalidates old approvals until the owner approves again.
- The installer runs a module's helper at approval time. It is the owner's approved, pinned code, run through the
  same path as `wb run` and `wb check`, and a helper that misreports the region defeats the approval.
- A new owner-run command must be added to the harness `deny` list.
- This repository is not an installed project, so its own plans are approved by the owner's statement in session
  until `self-hosting`.

## Verification

Built and tested by plan `2026-10-22-plan-approval-records` (increments A to F). Accepted by the owner on
2026-10-22 with this evidence and these limits.

- A synthetic process module's `approval` field verifies and is refused on any other type or for a command or
  argument it does not declare (`tests/test_declarations.py`).
- The installer resolves exactly one declaring module, runs the command bounded (stdin closed, 4,096 bytes,
  30 s) and accepts exactly one report line (`tests/test_approvalcmd.py`).
- `approve-plan` and `plan-status` go through each refusal and status, the two-run check against a swapped plan,
  and the typed prefix (`tests/test_planapprovals.py`); the commands are in `OWNER_RUN` and `AGENT_SAFE` and the
  Claude module renders the `deny` for `approve-plan`.
- The `code-work` helper's `region` subcommand, with spoofed headings, fences, comments, quotations, list items
  and HTML headings unable to hide a hashed section, and an installed-project run of `approve-plan` then
  `plan-status` (`packages/workbench/code-work/tests/`).
- The boundary test passes with the installer naming no plan section.
- A security review and a bypass attempt found two Medium region gaps, now fixed, and a workflow review found
  no Critical or High finding; the plan's Review record lists them. Not done: a hand run in a live installed
  project, and approving this repository's own plans with the command (needs `self-hosting`).

## Related files and decisions

- `docs/specs/trust-and-approval.md`, `docs/specs/code-work.md`, `docs/specs/module-contract.md`,
  `docs/specs/installer-interface.md`
- [2026-10-19-mandatory-review-personal-delegation](2026-10-19-mandatory-review-personal-delegation.md)
- [2026-10-19-guarded-store](2026-10-19-guarded-store.md)
- [2026-10-21-module-code-lives-in-modules](2026-10-21-module-code-lives-in-modules.md)
- [2026-10-22-plan-check-in-the-shipped-helper](2026-10-22-plan-check-in-the-shipped-helper.md)
