# Installer core and the declaration verifier

Status: Approved
Created: 2026-10-19
Candidate: workbench-v1#installer-core-verifier
Specs: module-contract, repository-boundary

## Goal

The first code of the workbench: a small installer core whose every write stays inside
one target directory, and a verifier that reads a package and its modules and accepts or
refuses them exactly as `module-contract` states. The verifier is reachable from a
`verify` command, writes nothing, and fails closed: when any module fails, the answer for
the package is a refusal.

## Scope

- A Python package `workbench/` at the repository root and its tests in `tests/`.
- The safe filesystem layer, ported deliberately and with tests from the old template's
  `install.py` (`safe_relpath`, `reject_git_metadata`, `read_regular`,
  `check_write_paths`, `write_tree` and the containment checks). It is built and tested
  here, but nothing in this plan calls its write functions on a project.
- The canonical declaration hash and the content tree hash.
- Parsing and validation of `package.json` and `module.json`, including names, versions,
  types, capabilities, `writes` paths and the closed set of fields.
- Module-against-files verification: accounted-for files, symbolic links, declared
  sources, and the harness item layout rules the contract states.
- Set verification for a selection of modules: type counts, requirements, conflicts,
  install order and cycles.
- A `verify` command with exit codes and a readable report.
- Record the concrete field names and formats in the specs, and the language choice as a
  decision, once the owner has seen them working.

## Non-goals

- Writing into any project. No install, attach, upgrade, manifest, seed, project ID or
  harness step. `write_tree` exists and is tested, and the `verify` command never calls
  it.
- The guarded store, approvals, hard-stop floor, package download, and the `wb`
  launcher (`module-approvals`).
- The installer's full command line and the target rules (`installer-interface`).
- Deleting files. The old `delete_files` is not ported; removal and upgrade need it
  later.
- Translating neutral harness items, rendering permissions, or validating a harness
  `layout` beyond its shape (`claude-harness`).
- Network access, fetching a package, or running anything a module ships or declares.
- Committing or pushing. Each increment is one local commit that the owner asks for.

## Assumptions and constraints

- **Language and layout are my calls for the owner to confirm at approval.** Python 3
  with the standard library only; `python3` here is 3.14.6, and the minimum version the
  code needs is found in Increment A and written into `docs/development.md`. No
  dependency is installed or added. Tests use `unittest`, run with
  `python3 -m unittest discover -s tests`. The entry point is `python3 -m workbench`.
  The code is in `workbench/` at the root, not under `src/`, so no path setup is needed.
- **Field names and value formats are the plan's proposals** and are what Increment D
  makes concrete: unknown fields are refused, duplicate JSON keys are refused, and a
  declaration larger than 1 MB is refused. A name is lowercase kebab-case, at most 64
  characters (`^[a-z][a-z0-9-]*$`). A version is one to four dot-separated non-negative
  integers without leading zeros, compared numerically. A capability has no spaces, is
  printable ASCII, and is at most 64 characters. `requires` entries are a capability
  string or `{"capability": "...", "soft": true}`. `fills` entries are
  `{"slot": "...", "source": "..."}`. `ships` and `writes` are lists of relative paths.
- **Hashing is SHA-256.** The declaration hash is taken over the declaration serialized
  as UTF-8 JSON with sorted keys at every level and no insignificant whitespace. The tree
  hash is taken over the sorted list of `path`, content hash and whether the owner
  execute bit is set, for every regular file in the module; the execute bit is included
  because hooks and helpers are code-bearing. The exact serialization is written down in
  Increment C and fixed by a known-answer test, so an approval made against it stays
  valid.
- **Verification takes a package, optionally a selection.** The per-module checks
  (declaration, files, hashes) run on every module in the package. The set checks (type
  counts, requirements, conflicts, order) run on the selected modules only, because a
  package may legitimately hold two harness modules and the project installs one. With
  no selection only the per-module checks run. The library accepts several packages so
  that a requirement can be met by a capability from another package, as the contract
  allows; the `verify` command takes one package. Multi-package selection on the command
  line is left to `installer-interface`.
- **First-party status is a parameter, not an input.** The check that a third-party
  package may not provide an unprefixed name takes `first_party` as an argument that
  defaults to false. The command cannot set it. Where it comes from belongs to
  `module-approvals`.
- **The target rule from the roadmap applies to the command's one path argument.** The
  package to verify may be given as a positional `<package>` or as `--dir <path>`, with
  the same meaning, defaulting to `.`; two different values are refused.
- The verifier reads files and never executes, imports or evaluates anything it reads. A
  module containing a symbolic link, a device, a socket or a FIFO is refused. It reads
  each file at most once and with a size limit.
- The old template is read only, for its safe-write rules and tests. Nothing is copied
  wholesale, and nothing is imported from it.
- No commit exists for this work yet, so nothing is migrated. Each increment is
  reviewed before its commit.

Discovery: skipped. The repository has no code and no discovery tooling, and the
affected files are enumerated below.

## Completion criteria

- Every acceptance criterion in `module-contract.md` that is about verification is
  covered by a named test that passes: unsupported or malformed package declaration,
  reserved names, two harness or two process modules, hard and soft requirements,
  requirements for harness capabilities, conflicts in either selection order, the
  provide-and-block case, unaccounted files, missing declared paths, symbolic links,
  `writes` escapes, prefix rules, hash equality and difference, and all-or-nothing.
- The ported safe-write rules each have a test: a path through a symbolic link, a
  destination that is a symbolic link or a non-file, `.git` in any case or with trailing
  dots and spaces, absolute paths, `..` segments, backslashes and drive letters, a
  parent swapped for a symbolic link after the check, atomic replacement that leaves no
  partial file, and a target that is a symbolic link. The reader used for verification
  has its own tests: a symbolic-link root, an ancestor swapped after validation, a file
  replaced by a symbolic link or by a different regular file after listing, a file
  modified during the read, a same-size rewrite with the modification time restored, a
  FIFO or device, and a file that grows during the read. A write cannot be redirected
  by a parent swapped for a symbolic link before the rename.
- `python3 -m workbench verify` accepts a valid sample package with exit code 0, refuses
  each invalid sample with exit code 1 and a message naming the module and the rule, and
  exits 2 on a usage error.
- A run of `verify` leaves the package directory byte for byte unchanged and creates no
  file anywhere, shown by a test that compares the tree before and after.
- `docs/development.md` lists the real commands. The specs record the concrete field
  names and formats, with the Deferred item for them closed. A decision record for the
  implementation language exists and is accepted by the owner.
- The full test suite passes on a clean checkout, and the independent review of each
  increment has no unresolved finding.

## Increments

### Increment A — Package skeleton and test runner

Dependencies: None
Affected areas: `workbench/__init__.py`, `workbench/__main__.py`, `tests/`,
`.gitignore`, `docs/development.md`

1. Create the `workbench` package with a `__main__` that prints usage and exits 2, and
   a `tests/` directory with one passing test that imports the package.
2. Add `__pycache__/` to `.gitignore`.
3. Find the lowest Python 3 minor version the code can use from the language features
   written so far, and record it in `docs/development.md` with the test command, the
   run command, and the statement that no dependency is installed.

Verification: `python3 -m unittest discover -s tests` passes; `python3 -m workbench`
exits 2 with usage; `git status --short` lists only the intended files.
Completion: the commands in `docs/development.md` run as written.

### Increment B — Safe filesystem layer

Dependencies: A
Affected areas: `workbench/safefs.py`, `tests/test_safefs.py`

1. Port `safe_relpath` and `reject_git_metadata` as one relative-path validator that
   refuses absolute paths, empty or `.` or `..` segments, backslashes, drive letters and
   colons, non-printable or over-long paths, and any segment equal to `.git` after
   case folding and trimming trailing dots and spaces.
2. Port `read_regular` and extend it into a race-safe reader, because the old one
   guarded only the final path component. The package and module roots must be real
   directories (not symbolic links). Every directory is opened with no-follow flags,
   relative to its parent's descriptor, so a parent swapped for a symbolic link after
   validation fails to open and cannot redirect a read. Each file is opened with
   no-follow and non-blocking flags relative to its directory descriptor. When a
   directory is listed, each entry's identity (device, inode, type, size, modification
   time and change time, `st_ctime_ns`) is taken through the directory descriptor
   without following links. The change time is included because userspace cannot
   restore it, so a rewrite of the same size with the modification time put back is
   still detected; its precision is the filesystem's, which is recorded in the module
   docstring as the limit of the check. After the open, `fstat` on the descriptor must show the same identity and a
   regular file within the size limit before anything is read; at most one byte over
   the limit is read; and a final `fstat` after the read must still show the same
   identity. Any mismatch, including a regular file replaced by a different regular
   file, is a refusal that names the path. If the platform lacks the no-follow and
   directory-relative open support the reader needs, the verifier refuses to run and
   says so.
3. Port `check_write_paths` and `write_tree`, made descriptor-relative: the root and each
   parent directory are opened with no-follow flags and held, each file is staged in an
   exclusively created temporary sibling created through its parent's descriptor, and
   it is replaced with a rename that names both parent descriptors (`src_dir_fd` and
   `dst_dir_fd`), never a path. Refuse writing through a symbolic link, onto a non-file
   or a read-only file, and remove stragglers on failure. Nothing writes outside the
   original root, even if a parent is swapped for a symbolic link after the check. If
   the platform lacks the support, the write functions refuse to run and say so.
4. Port the containment helpers (`real_directory`, `is_within`) with identity checks, so
   a case variant or a symlinked ancestor cannot place a path outside its root.
5. Write the tests listed in the completion criteria for the safe-write rules, adapting
   the old template's tests where they exist and adding the parent-swap and atomic
   replacement cases. The parent-swap test for writes is deterministic: the test injects
   a hook that swaps a parent directory for a symbolic link after the check and before
   the rename, and asserts the write lands inside the original root or is refused. For
   the reader, add adversarial tests: a module or package root that is a symbolic link,
   an intermediate directory swapped for a symbolic link after validation, a file
   replaced by a symbolic link or by a different regular file between listing and open,
   a file modified between the open and the end of the read, a rewrite of the same size
   with the modification time restored, a FIFO or device at a file path, and a file that
   grows past the limit while being read. Each must be refused without reading outside
   the package.
6. Do not port `delete_files`. Record in the module docstring that deletion is not
   provided yet.

Verification: the new tests pass; a search shows no function in `workbench/` calls
`write_tree` outside tests.
Completion: every safe-write rule in the completion criteria has a passing test.
Review: independent review including the security reviewer, because this is filesystem
code.

### Increment C — Hashing

Dependencies: B
Affected areas: `workbench/hashing.py`, `tests/test_hashing.py`

1. Implement the canonical serialization and the declaration hash.
2. Implement the tree walk and the tree hash over regular files only, using only the
   race-safe reader and directory walk from Increment B and the path validator, never a
   path-based `open` or `os.walk`. A symbolic link, device, socket or FIFO anywhere in
   the tree raises a refusal that names the path.
3. Write down the serialization in the module docstring. Fix both hashes with
   known-answer tests, including a fixture that proves field order and whitespace do not
   change the declaration hash, a changed value does, and a changed execute bit changes
   the tree hash.

Verification: the tests pass, and running them twice on a freshly created copy of the
fixture gives identical hashes.
Completion: the declaration hash and tree hash are deterministic and fixed by
known-answer tests.
Review: independent review.

### Increment D — Declaration parsing and validation

Dependencies: C
Affected areas: `workbench/declarations.py`, `tests/test_declarations.py`,
`tests/fixtures/`

1. Parse `package.json` and `module.json` with a strict loader: UTF-8 only, duplicate
   keys refused, size-limited, top level an object, and no value evaluated.
2. Validate each field against the formats in the assumptions. Refuse an unknown field.
   Refuse a package `contract` greater than the highest the verifier supports (1).
3. Refuse reserved names (`local`, `neutral`, anything beginning `manifest`) for package
   and module names, and require every module listed in a package to exist as a
   directory with the same name, with no extra module directory. The package list
   entry, the directory name and the `name` in `module.json` must all be equal; any
   mismatch is a module declaration error.
4. Validate capabilities: harness capabilities only from a `harness` type module; an
   unprefixed provided name only when `first_party` is true; a prefixed name's prefix
   equal to the package name; slots named `slot:<name>`; `layout` present for a harness
   module and absent otherwise, and an object whose keys come from the contract's table.
5. Validate every `writes` path with the path validator and reject any path inside
   `.workbench/<package>/<other module>/` or under the guarded store name.
6. Build sample packages in `tests/fixtures/` (one valid, and one per refusal, including
   a list entry, directory and declared name that disagree) and test each acceptance
   criterion about declarations.

Verification: the tests pass. Each refusal names its scope: a package-level problem
(for example a malformed package declaration, an unsupported `contract`, or a bad
package name) names the package and the field or rule, and a module-level problem
names the module and the field or rule.
Completion: each declaration-level acceptance criterion has a passing test.
Review: independent review.

### Increment E — Module files against the declaration

Dependencies: D
Affected areas: `workbench/modulefiles.py`, `tests/test_modulefiles.py`,
`tests/fixtures/`

1. Walk the module with the Increment C tree walk (the race-safe reader; no other
   file access) and classify every file as accounted
   for (`module.json`, under `harness/`, `templates/` or `files/`, or named by `fills`
   or `ships`) or not. A file that is not accounted for refuses the module.
2. Require that every `fills` source and `ships` item exists, and that every `writes`
   entry has its source at the same relative path under `files/`.
3. Apply the harness layout rules from the contract: at least one of `harness/neutral/`
   and a `harness/<name>/` directory exists in a module that supplies harness items; an
   `exclude` entry names an item that exists in `harness/neutral/`; an item both
   overridden and excluded is an error; every exclusion is reported as a warning. The
   item's kind and name come from the neutral item's directory and file name as
   `claude-harness` will define them; this increment fixes only the file-level checks
   and records the naming it assumed in the module docstring.
4. Compute and return the declaration hash and tree hash for the accepted module.

Verification: the tests pass and cover an unaccounted file, a missing declared source, a
symbolic link, a FIFO, and each harness layout rule.
Completion: the module-level acceptance criteria have passing tests.
Review: independent review including the security reviewer.

### Increment F — Set verification and the all-or-nothing result

Dependencies: E
Affected areas: `workbench/verify.py`, `tests/test_verify.py`

1. Define the result: accepted or refused, a list of problems (module, rule, message)
   and a list of warnings, and for each accepted module its two hashes.
2. Verify every module in each package, then the selection: at most one `harness` and
   one `process` module, a harness module present when a harness is required (a
   parameter, default true), hard and soft requirements, the harness-capability and slot
   rules that always make a requirement soft, helpers looked up on `PATH` as warnings
   only, and conflicts checked symmetrically after requirements.
3. Compute the install order as the contract states it: harness, then process, then the
   rest, and within each group a module follows the modules it requires. A requirement
   that points to a module in a later group (for example `code-work`, a process module,
   needing a capability that `groundwork` provides) is allowed and is not an error,
   because every requirement is resolved before any file is written and group order
   does not affect whether it is satisfied. Only a cycle in `requires` is a problem,
   and it names the cycle. The contract is ambiguous about such cross-group edges;
   Increment H asks the owner to rule on its wording. A test covers the `code-work` to
   `groundwork` edge.
4. If any module fails any step, the result is refused for the whole package. Nothing
   in this layer writes.
5. Test both orders of the conflict rule, the provide-and-block case alone and with a
   second provider, a cross-package hard requirement met and unmet, and a missing
   helper.

Verification: the tests pass, and a test creates a failing module among valid ones and
asserts the package result is refused.
Completion: the set-level acceptance criteria have passing tests.
Review: independent review.

### Increment G — The verify command

Dependencies: F
Affected areas: `workbench/cli.py`, `workbench/__main__.py`, `tests/test_cli.py`,
`docs/development.md`

1. Implement `python3 -m workbench verify [<package> | --dir <path>] [--select <module>
   ...] [--no-harness-required]`. Neither argument means `.`; the same path given both
   ways is accepted; two different paths are refused with exit code 2.
2. Print an accepted package as one line per module with its version and the first
   twelve characters of each hash, then warnings. Print a refusal as one line per
   problem naming its scope (the package or the module) and the rule. The CLI tests
   assert both a package-level and a module-level refusal. Exit 0 accepted, 1 refused, 2 usage error.
3. A test confirms that the command leaves the package tree unchanged and creates no
   file anywhere, comparing a full listing with hashes before and after, on both an
   accepted and a refused package.
4. Add the commands and exit codes to `docs/development.md`.

Verification: the tests pass, and the commands in `docs/development.md` run as written
on the valid fixture and one invalid fixture.
Completion: the command meets its completion criteria.
Review: independent review.

### Increment H — Record the concrete schema and the decision

Dependencies: G
Affected areas: `docs/specs/module-contract.md`,
`docs/decisions/2026-10-19-implementation-language.md` (proposed),
`docs/roadmaps/workbench-v1.md`, this plan

1. Edit `module-contract.md` in place so the field names, formats, hash serialization
   and limits match what the code accepts, and remove the first Deferred item. Review
   item 12 on overloaded terms stays open unless the code showed a clash; record any
   clash found. Ask the owner to rule on the cross-group requirement wording in the
   install order (Increment F, step 3) and write the ruling into the spec.
2. Draft a decision record, `Status: Proposed`, for Python with the standard library
   only, tests with `unittest`, and no dependencies. Accepting it is the owner's act.
   If the owner declines it, the plan stops: it is re-approved with a different
   language or superseded, and it is not marked complete.
3. Update the roadmap's current state. Do not mark the candidate complete; completion is
   derived from this plan's status.
4. Fill in this plan's Result.

Verification: a reading of the spec against the code and fixtures shows no field or
format the code accepts and the spec does not state, and the reverse.
Completion: the spec edit exists and the owner has accepted the decision record. A
declined decision does not complete the increment.
Review: independent review of the spec edit only if the owner asks.

## Verification

- `python3 -m unittest discover -s tests` passes in full.
- `python3 -m workbench verify` on the valid fixture exits 0, and on each invalid
  fixture exits 1 with a message naming the module and the rule.
- The tree-unchanged test passes for both outcomes.
- Every acceptance criterion in `module-contract.md` about verification maps to a named
  test, listed in this plan's Result.
- `git diff --check` is clean, and no file outside the enumerated areas changed.

## Risks and sensitive actions

- **A hash format fixed too early.** Approvals bind to these hashes, and a later change
  invalidates them. Mitigation: the format is written down, fixed by known-answer tests,
  and shown to the owner in Increment C before anything depends on it. Nothing is
  approved yet, so a change costs only tests.
- **Filesystem code.** The safe layer is the part most likely to hide a path-escape or
  race. Mitigation: it is ported with its tests, the parent-swap case is added, and
  Increments B and E get the security reviewer.
- **Reading hostile input.** A package is untrusted. The verifier only reads, with size
  limits, no-follow opens and a strict loader, and never executes or evaluates.
- **Two spellings of the path argument.** Accepting `<package>` and `--dir` could hide a
  disagreement. Mitigation: two different values are refused.
- **Harness item naming assumed.** Increment E assumes how an item's kind and name are
  read from the layout. If `claude-harness` needs a different rule, that increment's
  checks change. Mitigation: the assumption is recorded in the code and is limited to
  file-level checks.
- **Python choice.** The language is not in the specs. It is an assumption to approve,
  and Increment H turns it into a decision the owner accepts.
- Sensitive actions: none. No commit, push, network access, dependency install, secret or
  deletion is part of any increment; commits are made only when the owner asks, with
  the commit helper.

## Review record

Reviewed by Codex (model `gpt-5.6-luna`) on 2026-10-19, at the owner's request, after the
owner had approved the plan. Three rounds, the bound; the owner declined a fourth. Round 1
and 2 ran at the helper's default effort and round 3 at high. Each edit below was
approved by the owner before it was made.

- **R1-F1** (major): the reader guarded only the final path component. Applied:
  descriptor-relative, no-follow reading with root validation and adversarial tests.
- **R2-F1** (major): a regular file replaced by a different regular file could not be
  detected. Applied: file identity is captured at listing and compared after open and
  after the read.
- **R2-F2** (major): the plan lacked required sections. Rejected: all required sections
  were present (Verification, Risks, Review record, Deferred work, Result), so the finding
  rested on a truncated view of the file.
- **R3-F1** (major): the write path replaced by path and could be redirected by a swapped
  parent. Applied: descriptor-relative staging and rename, and a deterministic test.
- **R3-F2** (major): a same-size rewrite with the modification time restored passed.
  Applied: change time added to the identity, with its limit recorded.
- **R3-F3** (major): the declared module name need not equal its list entry. Applied:
  the list entry, directory and declared name must be equal.
- **R3-F4** (major): the install order is ambiguous for requirements across groups.
  Applied: only a cycle is an error, and Increment H asks the owner to rule on the
  contract's wording.
- **R3-F5** (major): package-level errors cannot name a module. Applied: errors name
  their scope, the package or the module.
- **R3-F6** (major): a declined language decision would still complete Increment H.
  Applied: completion requires acceptance.

The edits made after round 3 have not been re-reviewed. The plan stays `Approved`.

## Deferred work

- The installer's full command line and target rules: `installer-interface`.
- The store, approvals, floor, download and launcher: `module-approvals`.
- Deleting files safely: `ownership-and-upgrade` and `code-work-module`.
- Validating a harness `layout` beyond its shape: `claude-harness`.
- Multi-package selection on the command line, machine-readable output (`--json`) and
  verbosity options.

## Result

In progress. Increments A to E are committed (`89d64c6`, `3f6b6ec`, `2b53cd0`,
`92fe5fa`, `eab70b6`) and the review fixes for E follow them. The full suite passes
(165 tests, `python3 -m unittest discover -s tests`). Increments B and E had a security
review whose findings were fixed with tests; C and D had no independent review yet.

Calls made in D and E that the owner has not yet confirmed, to be written into the spec
in Increment H: a `writes` path may enter `.workbench/` only under the module's own
namespace; a path beginning `.config/project-workbench` is refused; `slots` lists owned
slot names and `provides` may not list `slot:` entries; `fills` takes `slot:<name>`;
`type` defaults to `module` and only `name`, `version` and `description` are required;
dotted sub-names are refused; harness item naming is `<kind>/<name>` as the
`modulefiles` docstring states; an empty directory in `ships` is refused.

Next: Increment F (set verification and the all-or-nothing result).
