# Python with the standard library only for the installer

Status: Accepted
Date: 2026-10-19

## Context

The installer reads untrusted package declarations and files, and later writes into a
user's project. The old template's installer was Python 3 with no dependencies, and the
repository assumes git, a POSIX shell and `python3` (`docs/specs/repository-boundary.md`).
The language was not in the specifications, so `installer-core-verifier` started with
Python as an assumption for the owner to confirm. That candidate has now built the safe
filesystem layer, hashing, declaration parsing, module and set verification and the
`verify` command in it.

## Decision

The installer and its tools are written in Python 3 using only the standard library. No
dependency is installed or added. Tests use `unittest`, run with
`python3 -m unittest discover -s tests`, and the entry point is `python3 -m workbench`.
The code lives in `workbench/` at the repository root. The minimum Python version is the
one recorded in `docs/development.md`; the checks have been run only on Python 3.14.
A later dependency needs its own decision record.

## Alternatives considered

- **A compiled language (Go or Rust).** Rejected for now: a build step and a toolchain
  become prerequisites for every user, while the installer's work is file handling that
  Python's standard library covers, including descriptor-relative opens.
- **POSIX shell.** Rejected: strict JSON parsing, hashing and the race-safe file
  handling this installer needs are not practical to make safe in shell.
- **Python with third-party packages.** Rejected: a dependency is code the installer
  would run before it has verified anything, which conflicts with treating every package
  uniformly and with a small, auditable base.

## Consequences

- Every machine that runs the installer needs `python3`. A platform without the
  descriptor-relative open support (likely Windows; not tested) is refused by the
  reader, which says so.
- The race-safe filesystem layer relies on `O_NOFOLLOW`, `O_DIRECTORY` and directory
  descriptors, as the platform provides them.
- The oldest interpreter is not tested. The minimum version is derived from the language
  features used.
- If the owner declines this record, the plan `installer-core-verifier` stops: it is
  re-approved with a different language or superseded, and it is not marked complete.

## Verification

`python3 -m unittest discover -s tests` passes in full, and
`python3 -m workbench verify tests/fixtures/sample-package --select sample-harness
sample-notes` exits 0, as `docs/development.md` states.

## Related files and decisions

- `docs/plans/2026-10-19-installer-core-verifier.md`
- `docs/development.md`, `docs/specs/repository-boundary.md`
