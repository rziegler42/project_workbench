# The installer runs the document checks, for a project that has the module

Status: Accepted
Date: 2026-10-21

## Context

The groundwork specification asks a check to report a wrong document name or status, a superseded
record with no successor, a duplicate candidate ID in one roadmap and a reference index that
disagrees with git. `groundwork` ships no code and no helper, and the project's rules say each
check is enforced by the installer once it is built. A check must also read untrusted repository
content: files that anyone who can commit may write, behind folders that may be links.

## Decision

- `wb check` runs the document checks itself, in `workbench/doccheck.py` and the reference check
  that follows it. The module declares nothing about them and ships no code.
- A check runs only for a project whose committed manifest records the module `groundwork` of the
  package `workbench`. A project without it, including one with a hand-written `docs/specs`, gets
  no report from these checks. A project with the module and none of the folders gets none either.
- The checks read through the same no-follow reader and bounded budgets as the rest of `check`,
  run no program, and write nothing. Passing a bound is a problem that says what was not looked at.
- The rules are the ones the module's READMEs state: names, the status values of each kind, a
  `Superseded by <name>` line for a superseded record, and candidate IDs as lowercase kebab-case
  slugs that are unique after Unicode folding. Roadmap status values are `Draft`, `Active` and
  `Archived`.

## Alternatives considered

- **A `checks` field in the declaration** naming built-in checks. More general, and a new field in
  the module contract with a trust question of its own (what a third-party module may ask the
  installer to run). Nothing but this module needs it yet. Rejected for now.
- **A check shipped as module code.** Rejected: it would be code that reads hostile repository
  content, approved per module, and `groundwork` is meant to ship none.
- **Running the checks for every project.** Rejected: a project that does not use the module has
  not agreed to its naming and status rules.

## Consequences

- A later module that wants a check needs either a new decision that adds the `checks` field or a
  change to the installer. This record is the precedent for the second.
- The key is the package and module name the manifest records. A package that calls itself
  `workbench` and a module `groundwork` gets the checks; they only report, so the cost is a
  report on a project that chose such a package.
- A heading inside an HTML comment still counts as a candidate, and a document of the wrong kind
  in a folder is read as the folder's kind.

## Verification

Tests of the plan `2026-10-21-groundwork-module` (increment F), `tests/test_doccheck.py`: each
rule, the hostile cases of the plan's Review focus 1, 4 and 5, and the end-to-end command on a real
git repository without attaching a harness.

## Related files and decisions

- `docs/specs/groundwork.md`
- `workbench/doccheck.py`, `workbench/check.py`
- [2026-10-20-first-party-by-location-and-shipped-record](2026-10-20-first-party-by-location-and-shipped-record.md)
- [2026-10-19-tracked-pointer-rule](2026-10-19-tracked-pointer-rule.md)
