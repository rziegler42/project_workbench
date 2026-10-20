# Nothing tracked in a document or workbench-managed file depends on untracked content

Status: Accepted
Date: 2026-10-19

## Context

A clone has files that others do not: scratch, harness files and untracked references. A
tracked document that links to one is broken for every other clone, and may point a
reader or an agent at content nobody reviewed.

## Decision

No tracked document or workbench-managed file may depend on an untracked or ignored file:
no link, include, import or citation by path. A tracked document cites an untracked
reference by source URL, retrieval date and content hash, never by path. The rule covers
documents, manifests and files the workbench writes. It does not cover a project's source
code or build outputs, which may use generated or fetched files. Naming a convention path
in prose is allowed. A check flags links, includes and imports that point into untracked
or ignored locations and ignores plain text mentions. The tracked reference index records
only tracked files, with a separate untracked index in scratch.

## Alternatives considered

- **Allow pointers with a warning.** Rejected: broken for every other clone.
- **Apply the rule to source code.** Rejected: legitimate generated files exist.
- **Track everything.** Rejected: license and size make that wrong for many references.

## Consequences

- Authors cite outside material by URL, date and hash.
- The check needs to recognize links and includes in documents, not source code.

## Verification

Acceptance criteria in `docs/specs/repository-boundary.md` and `docs/specs/groundwork.md`:
a tracked file that links into `.workbench/local/` is reported, a plain mention is not, and
the tracked reference index contains no untracked file.

## Related files and decisions

- `docs/specs/repository-boundary.md`, `docs/specs/groundwork.md`
- [2026-10-19-harness-files-per-clone](2026-10-19-harness-files-per-clone.md)
