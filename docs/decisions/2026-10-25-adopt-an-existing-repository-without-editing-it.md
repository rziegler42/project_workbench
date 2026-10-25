# Adopt an existing repository without editing it

Status: Proposed
Date: 2026-10-25

## Context

The installer refuses a directory that has content. The decision `2026-10-20-target-decided-by-state` made that
deliberate: a target is new, existing or refused, decided from files and without git, and `install` creates every file
exclusively, so an existing path is a conflict for the owner. That is right for a new project and it leaves no way
into a repository that already exists, including this one. The workbench's own gates (the edit gate, the plan check,
`wb approve-plan`) therefore cannot apply to the workbench's own work, which the owner enforces in session today.

The parts adoption needs exist. `upgrade` already classifies a present seeded file **skip** and offers a slot block as
**create** or **append** on approval. `attach` already leaves a file that equals the planned bytes and refuses any
other. What is missing is a way to enter a populated directory that is a promise of its own: it must never edit a file
that is there.

## Decision

1. **A new command, `adopt`, not an option on `install`.** `install` promises a new project and nothing else, and tests
   and the specification pin it. `adopt` takes `install`'s arguments, is previewed by `wb preview adopt`, is owner-run
   and terminal-only, and is denied to an agent by every harness as `install` is.
2. **Adoption never edits an existing file.** It creates what is missing, reuses an existing real directory, and writes
   nothing into any other existing path. A path a module owns, or one of the wrong type or behind a link, refuses the
   whole command with every conflict listed. A slot block whose file exists is not filled; the preview names the file,
   the slot and the `wb upgrade` that offers it.
3. **A kept seeded file is recorded with the hash of the bytes there**, as owner class `seeded`. The manifest records
   the bytes the installer last saw, and "seeded with an entry is skip always" already makes a later edit the project's.
4. **`adopt` requires the target's own real `.git` directory** and no `.workbench` entry of any kind. It does not
   initialize a repository, run git or read repository configuration, and it refuses a `.git` file or link.
5. **`adopt` does not attach.** The edit gate is rendered into per-clone harness files by `attach`, which stays its own
   owner-run command and keeps its rule that an existing file with other content is a conflict. An adopted project is
   installed but not gated until `wb attach` has run.

## Alternatives considered

- **`install --adopt`.** Rejected: it changes the meaning of a command the owner has learned to trust, and the riskier
  operation would not show in the command line.
- **Appending the blocks during `adopt`.** Rejected: it puts the first edit of a hand-written file inside the riskiest
  command. `upgrade` already offers the append on approval.
- **Recording the seed's hash for a kept file.** Rejected: it says the file is something it is not, and `upgrade`
  would later report a hand-written file as an edited seed.
- **Running `attach` from `adopt`.** Rejected: harness files may already exist and are the owner's, and a conflict
  there would leave a half-finished adoption.
- **Adopting a directory with no `.git`.** Rejected: such a directory is not a repository, and the installer does not
  initialize one next to someone's files.

## Consequences

- A repository with content can become an installed project in two owner-run steps, `adopt` and `attach`, with
  `upgrade` to fill the blocks it left.
- The new command is the riskiest write path the workbench has: it enters a populated, possibly untrusted directory.
  The plan requires an independent security review of it before the lifecycle tests and before this repository is
  adopted.
- The unfinished-write marker may record a kept file as unchanged, and `recover` must never write or remove one.
- `adopt` joins the owner-run commands, so the rendered deny rules and the specifications that list them change.
- Reconciling the text of a kept file with its seed is not done by `adopt`; it is a later, ordinary edit.

## Verification

Not built. The specifications are `docs/specs/installer-interface.md` ("States of a target", "`adopt`"),
`docs/specs/repository-boundary.md` and the owner-run lists in `docs/specs/trust-and-approval.md` and
`docs/specs/harness-modules.md`. The plan `docs/plans/2026-10-25-adopt-existing-repository.md` builds and tests it in
increments B to E and adopts this repository in increment F.

## Related files and decisions

- `docs/specs/installer-interface.md`, `docs/specs/repository-boundary.md`
- `docs/plans/2026-10-25-adopt-existing-repository.md`
- [2026-10-20-target-decided-by-state](2026-10-20-target-decided-by-state.md)
- [2026-10-20-preview-then-owner-run-write](2026-10-20-preview-then-owner-run-write.md)
- [2026-10-19-non-destructive-upgrades](2026-10-19-non-destructive-upgrades.md)
