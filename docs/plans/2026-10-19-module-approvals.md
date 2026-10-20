# The guarded store and module approvals

Status: Approved
Created: 2026-10-19
Candidate: workbench-v1#module-approvals
Specs: trust-and-approval, repository-boundary, module-contract

## Goal

Make the workbench able to say, from a place the agent cannot write, whether a module
has been approved on this machine, and refuse when it has not. Every command ensures the
user-level guarded store exists and is seeded. The hard-stop floor is compiled in and
also seeded into the personal settings. A package is downloaded inertly into the store's
cache, shown to the owner, and approved by a command the owner runs. A record binds to
the declaration hash and tree hash, so a changed module needs a new approval.
First-party approvals are generated at release time and read from the workbench
distribution. The `wb` launcher runs a pinned helper only after checking its hash.

When this plan is done, a later installer asks one function whether a verified set of
modules is approved, and the answer is no unless every module has a matching record.
No project is written by anything in this plan.

## Scope

- The guarded store at `~/.config/project-workbench/`: its location, creation,
  permissions, layout (`settings`, `packages/`, `cache/`, `projects/`) and idempotent
  initialization that every command runs first.
- The hard-stop floor as compiled code, the personal settings file with its seeded
  additive copy, and the checkpoint settings (`stop` by default, `delegate` only when set).
- Approval records for modules and packages: format, writing, reading, and verification
  against current hashes. A missing, unreadable or mismatched record is no approval.
- First-party approvals: a release-time generator, a reader of the records shipped in the
  distribution, and the rule that decides when a package is first-party. This supplies
  the `first_party` value that `installer-core-verifier` left as a parameter.
- The approval request: the declaration shown in plain terms, with high-risk flagging.
- The owner-run `approve` command.
- Inert download of a package into the cache, and the pin of its resolved commit and
  package tree hash at first approval.
- A gate function that answers whether a verified selection is fully approved, with
  nothing written when it is not.
- Pins and the `wb` launcher that verifies a helper's hash before running it.
- Record the concrete formats in the specs, and any durable choice as a decision record.

## Non-goals

- Writing into any project: no install, attach, upgrade, manifest, seed or project ID.
  The gate function exists and is tested; nothing calls it on a project yet.
- Plan approval, delegated approval, the delegation helper and the `peer-review`
  capability (`code-work-module`). Only the settings that name a checkpoint exist here.
- Acknowledgement baselines and the diff shown for changed files. The store directory
  for them is created; their contents are `base-and-manifests` and later.
- Rendering the floor, or a deny rule on the store, into any harness's configuration, and
  the validator that rejects an `allow` entry in the neutral rule list (`claude-harness`).
- The installer's full command line and its target rules (`installer-interface`). The
  commands added here are `approve`, `release-approvals` and `launch`, and nothing else.
- Fetching anything other than a package. The other channels in `trust-and-approval`
  belong to their own candidates.
- Windows. The store, the launcher and the permissions logic assume POSIX.
- Pushing, publishing, or installing dependencies. Commits are made only when the owner
  asks, with the commit helper.

## Assumptions and constraints

Everything here is a proposal for the owner to confirm at approval. The specs call record
formats and setting names proposals, and Increment K turns the ones that survive into
spec text.

- **Same stack.** Python 3, standard library only, `unittest`, the layout of
  `installer-core-verifier`. The new code uses the safe filesystem layer for every store
  read and write, and the existing verifier and hashes unchanged. No dependency is added.
- **The store location is fixed, not configurable.** It is `~/.config/project-workbench/`
  found from the account's home directory. There is no workbench environment variable that
  moves it, because a variable the agent can set in a command would let it point the
  workbench at a store it controls. The code takes the root as an argument so tests use a
  temporary one; the command line never exposes that argument. `HOME` itself is still
  honoured by the operating system, which is the same-account limit `trust-and-approval`
  already states.
- **The store root must be a real directory, its ancestors may be links.** `~/.config` is
  often a symbolic link into a dotfiles checkout. The store directory itself must not be a
  symbolic link, must be owned by the current user, and has mode `0700`; everything inside
  is opened with the no-follow, descriptor-relative layer and written atomically.
- **Settings are strict JSON in a file named `settings`.** It holds a version, the floor
  copy, and a `checkpoints` object mapping a checkpoint name to `stop` or `delegate`. It is
  loaded with the existing strict loader. A missing file is seeded. A damaged file is never
  overwritten: the command reports it, and every checkpoint behaves as `stop`.
- **The compiled floor always applies.** Effective stops are the compiled floor plus any
  added by modules. The seeded copy is only a convenience for the owner to read and for
  harnesses to render; no code path reads stops from the file in order to loosen them.
  How a module would declare an added stop is not in `module-contract`; this plan tests
  the addition and removal rules on the function that combines stops, and Increment K
  records the gap.
- **An approval record is a small JSON file** in `packages/<key>/` with a kind (`module` or
  `package`), the subject (`<package>/<module>` or `<package>`), the bound hashes, the
  approver (the operating-system user name), the time in UTC, and the workbench version
  that recorded it. `<key>` is the SHA-256 of the kind, the declaration hash and the tree
  hash. A record is valid only when its key, its stored hashes and the hashes just computed
  from the cached or installed copy all agree.
- **A package record binds more than a module record.** It holds the package's own
  declaration hash, its list of module names with their two hashes each, the resolved
  commit (when it came from a git source), and the package tree hash, which is the existing
  tree hash taken over the whole package directory. Approving a package approves exactly
  that module list; a module added later is a different package hash.
- **`harness` and `process` modules always need an explicit approval.** For a first-party
  package this is satisfied by the shipped record, which counts as explicit.
- **First-party means: the package directory lies inside the workbench distribution's
  `packages/` directory, and a shipped record matches its hashes.** Both hold or the
  package is treated as third-party. There is no first-party package yet, so the release
  generator and the reader are built and tested against a fixture distribution. The
  location of the real first-party packages is a call this plan makes and the roadmap
  does not.
- **The approval command needs a terminal.** `approve` refuses to run unless standard input
  and output are both terminals, prints the request, and accepts only the first twelve
  characters of the tree hash typed by the owner. There is no `--yes`. This is an
  inconvenience for an unattended agent, not a barrier: the barrier is the deny rule that
  `claude-harness` renders. The plan says so in `docs/development.md`.
- **Inert download uses git and reads objects, it never checks out.** The package is
  fetched into a bare repository inside the cache with hooks disabled and `GIT_*`
  variables scrubbed. Files are then read from the fetched tree object with `git ls-tree`
  and `git cat-file`, never by `git checkout`. Only regular files with mode 100644 or
  100755 are accepted; a symbolic link, a submodule, a path naming `.git`, or an
  oversize file refuses the download. The files are written under a fresh directory in the
  cache with the safe write layer. Nothing executes, and no filter, hook or LFS smudge
  runs. Source forms accepted are an `https://` URL, an `ssh` URL, and a local path or
  `file://` URL (used by tests and by an owner with a local checkout).
- **Network is used only by the fetch increment and never by tests.** Tests fetch from a
  repository they create in a temporary directory.
- **The launcher is a pin check, not a sandbox.** `launch` reads a helper through the safe
  reader, hashes it, compares with the pin in the store, copies those exact bytes to a
  private directory in the store, and executes the copy, so a swap after the check cannot
  change what runs. The pin file is `projects/<project-id>/pins`. The project ID does not
  exist until `base-and-manifests`; the pin functions take it as an opaque string, and the
  tests use a fixed one.
- **`wb` is a generated wrapper.** The store initialization writes `bin/wb`, a short POSIX
  shell script that runs `python3` on the workbench it was installed from. How the
  workbench itself is distributed and installed is not in the specs; this plan records the
  wrapper's assumption that the distribution is a directory on this machine, and leaves
  packaging to a later plan.
- Discovery: skipped. The code is a small, known tree; the affected modules are enumerated
  below and the only existing code touched is read through its public functions
  (`safefs`, `hashing`, `declarations`, `verify`).

## Completion criteria

- Every acceptance criterion in `trust-and-approval.md` that this plan can reach has a named
  passing test: with no personal settings every checkpoint behaves as `stop`; a module
  whose declaration or content differs from its approval is not approved and nothing is
  written; a committed `Status: Approved` line is never an approval; a module that tries to
  remove a floor entry is refused; a pulled edit to a pinned helper is not run until the pin
  is updated. The criteria that need a harness, a plan or acknowledgement are listed in the
  Result as not reached here.
- Every acceptance criterion in `repository-boundary.md` about the store is covered: a
  package newly named is not written or activated before its declaration is approved on
  this machine, though it may be downloaded inertly into the cache; and the store's layout
  is created idempotently.
- The store tests include: an existing store with a wrong owner or mode is refused; a store
  directory that is a symbolic link is refused; a damaged settings file is reported and not
  overwritten; two initializations in a row change nothing; a symbolic link planted inside
  the store is not followed; a record whose file name does not match its content is
  rejected.
- The download tests include: a repository containing a symbolic link, a submodule, a path
  naming `.git`, an oversize file and a path through `..` is refused with nothing
  left in the cache; a repository whose ref moves between two fetches gives the pinned
  commit, not the new one; and no file in the fetched tree is executed.
- `python3 -m workbench approve`, `release-approvals` and `launch` are documented in
  `docs/development.md` and run as written.
- The full suite passes on a clean checkout, and the independent review of each increment
  marked below has no unresolved finding.
- The specs record the concrete formats, the decision records exist, and the Result lists
  what was not reached.

## Increments

### Increment A — The guarded store and its initialization

Dependencies: None
Affected areas: `workbench/store.py`, `tests/test_store.py`, `workbench/cli.py`,
`tests/test_cli.py`, `docs/development.md`

1. Implement `Store(root)` and `default_root()`, which is the account's home directory plus
   `.config/project-workbench`. Check that the root, if it exists, is a real directory
   owned by the current user with no group or other permission bits; refuse otherwise and
   name the problem. Create it with mode `0700` and create `packages/`, `cache/`,
   `projects/` and `bin/` the same way. Open every level through the no-follow layer.
2. `ensure()` is idempotent and is the first call of every command. Make `cli.main` call it
   before dispatching `verify`. `main` takes a keyword-only `store_root` for tests that
   defaults to `default_root()`. It is not a command-line option and no environment
   variable sets it. Every existing and new CLI test passes a temporary root, so no test
   opens the real store. A failure to initialize stops the command with exit 1 and a
   message, and runs nothing.
   The earlier guarantee that `verify` creates no file anywhere changes, as the spec
   requires of every command: `verify` creates nothing in the package or elsewhere except
   the store. Update the tree-unchanged test in `tests/test_cli.py` to compare the package
   tree before and after, and to allow only the temporary store root to appear. Record the
   change in `docs/development.md`.
3. Reading and writing store files goes through `safefs` only. Add a small
   `Store.read(rel)` and `Store.write(rel, data)` that validate the relative path, refuse
   `..` and symbolic links, and write by staging and renaming.
4. Tests, using a temporary root passed as an argument, plus a guard that fails any test
   which opens the real default root: creation from nothing; a second
   call changes no byte and no mode; wrong mode, wrong owner (by monkeypatching the owner
   lookup), a symbolic-link root, a symbolic link planted at `packages`, and a file where a
   directory should be are each refused; `HOME` pointing elsewhere moves the default root
   and the test says so.

Verification: the new tests pass; the full suite passes without creating the real
store, shown by checking that the real path is still absent afterwards (this check comes
before the manual run below); a manual `python3 -m workbench
verify tests/fixtures/sample-package --select sample-harness sample-notes` run leaves the
real store created with mode `0700`, and a second run changes nothing.
Completion: initialization is idempotent and fails closed on every listed bad state.
Review: independent review including the security reviewer, because this is filesystem
code and the root of all trust.

### Increment B — The hard-stop floor and the personal settings

Dependencies: A
Affected areas: `workbench/floor.py`, `workbench/settings.py`, `tests/test_floor.py`,
`tests/test_settings.py`

1. `floor.py` holds the five floor entries from `trust-and-approval.md` as an immutable
   tuple of stable identifiers with a one-line description each, and
   `effective_stops(additions)`, which returns the floor plus the additions and raises on an
   addition that is malformed, duplicates a floor entry under another spelling, or asks to
   remove or relax one. There is no function that returns fewer stops than the floor.
2. `settings.py` defines the settings document (version, floor copy, checkpoints),
   `seed(store)` which writes it only when absent, and `load(store)` which returns the
   settings plus a list of problems. A damaged or unreadable file yields the default
   settings, every checkpoint `stop`, and a problem the command prints; it is not
   overwritten. A checkpoint value other than `stop` or `delegate` is a problem and reads
   as `stop`. A checkpoint missing from the file reads as `stop`.
3. Initialization (Increment A) calls `seed`. The seeded floor copy is additive: loading
   never reads the copy to decide what applies.
4. Tests: with no settings file every checkpoint is `stop`; a settings file that lists an
   empty floor, or deletes it, changes nothing about `effective_stops`; a hostile value for
   a checkpoint reads as `stop`; a module-added stop is included; a module asking to remove
   or rename a floor entry is refused; a damaged settings file survives initialization
   unchanged and is reported.

Verification: the tests pass and a search shows nothing reads stops from the settings file.
Completion: the floor cannot be shortened by any file, and every checkpoint defaults to
`stop`.
Review: independent review.

### Increment C — Approval records

Dependencies: A
Affected areas: `workbench/approvals.py`, `tests/test_approvals.py`

1. Define the module record and the package record as in the assumptions, with a strict
   parser that refuses an unknown field, a wrong type, a hash that is not 64 hex digits and
   a kind other than `module` or `package`. Compute the key from kind and hashes.
2. `record_module(store, subject, declaration_hash, tree_hash, approver, now)` and
   `record_package(...)` write one file each, atomically, refusing to overwrite a record
   with different content. They are internal; the only callers are the `approve` command
   (Increment G) and the release generator (Increment D).
3. `check_module(store, declaration_hash, tree_hash)` and `check_package(...)` return an
   `Approval` or a reason. They look the record up by key, parse it, check that its stored
   hashes equal the key and the hashes presented, and treat a missing, unreadable, mismatched
   or malformed record as no approval, each with its own reason. A record in the wrong
   directory, or whose file name differs from its key, is rejected.
4. Tests: round trip; a changed declaration hash and a changed tree hash are each not
   approved; a record edited by hand to carry another module's hashes is rejected; a
   truncated file, a symbolic link in place of a record and a record in a wrong directory
   are each no approval; two records for one subject at different hashes both stay valid and
   independent.

Verification: the tests pass.
Completion: an approval is valid only while the presented hashes equal the recorded ones.
Review: independent review including the security reviewer.

### Increment D — First-party approvals

Dependencies: C
Affected areas: `workbench/firstparty.py`, `workbench/approvals.py`,
`tests/test_firstparty.py`, `tests/fixtures/`, `docs/development.md`

1. `firstparty.py` locates the distribution root from the package's own location and reads
   shipped records from a directory beside the code. The reader uses the same record parser
   and never copies a record into the store.
2. `is_first_party(package_path)` is true when the package's real path lies inside the
   distribution's `packages/` directory and the package name is the one the shipped records
   name. `verify_package` gets its `first_party` value from this function in the command
   path; the existing parameter stays for tests.
3. The generator `release-approvals` verifies every package under the distribution's
   `packages/` with `first_party=True`, refuses to write anything if any module fails, and
   writes one module record per module and one package record per package, with a
   fixed time and approver value so the output is reproducible. It is a release-time
   command, documented as such.
4. `check_module` consults the shipped records first for a first-party package and the store
   second, and reports which one supplied the approval.
5. Tests on a fixture distribution: generation is byte-identical when run twice; a changed
   module file makes the shipped record stop matching; a third-party package that copies a
   first-party name is not first-party, because of its location; a shipped record is not
   copied into the store; a failing module stops generation with no file written.

Verification: the tests pass, and with no `packages/` directory the generator reports "no
first-party packages" and exits 0.
Completion: a package inside the distribution with a matching shipped record is approved; the
same files elsewhere are not.
Review: independent review.

### Increment E — The approval gate

Dependencies: C, D
Affected areas: `workbench/gate.py`, `tests/test_gate.py`

1. `check_selection(store, result)` takes the accepted `Result` from `verify_packages` and
   returns, for each module in install order, either its `Approval` or the reason it has
   none. The selection is approved only when every module is. A refused verification result
   is passed through as refused and nothing is looked up.
2. `harness` and `process` modules require a record of kind `module` for that module;
   a package record alone does not satisfy them.
3. The function reads the store and never writes it. Tests assert the store tree is
   unchanged, with hashes, before and after, in both outcomes.
4. Tests: all approved; one unapproved; one with a changed tree hash; a harness covered only
   by a package record; a refused verification; an empty store; first-party and third-party
   mixed.

Verification: the tests pass and a search shows no caller outside tests.
Completion: the gate answers "approved" only when every selected module has a matching
record, and writes nothing.
Review: independent review.

### Increment F — The approval request

Dependencies: C
Affected areas: `workbench/request.py`, `tests/test_request.py`

1. `render(package, module, hashes, source)` produces the plain-terms text the owner sees:
   type; what it provides, requires and blocks; the paths it writes; every item it ships,
   each marked as executable or code-bearing; the helpers it expects; and the two hashes in
   full. A module that blocks a core capability, or that is of type `harness` or `process`,
   is flagged high risk at the top.
2. The text is built only from the verified declaration. Every package-supplied string is
   passed through the existing output cleaner, so a hostile name or reason cannot inject
   terminal escape sequences or fake lines.
3. A package request lists every module of the package, with the ones that need explicit
   approval marked.
4. Tests, including a module whose names and ship entries carry escape sequences and
   newlines; the output contains none of them raw.

Verification: the tests pass; the output for the sample package reads correctly when run.
Completion: the request shows everything the specs list and nothing unescaped.
Review: independent review including the security reviewer, because the text is shown to the
person who decides.

### Increment G — The `approve` command

Dependencies: E, F
Affected areas: `workbench/cli.py`, `workbench/approve.py`, `tests/test_approve.py`,
`docs/development.md`

1. `python3 -m workbench approve <package-dir>` verifies the package with
   `verify_package`, refuses on any problem with nothing recorded, prints the request, and
   asks the owner to type the first twelve characters of the package tree hash. On a match
   it records the package and each module. Any other input records nothing.
2. The command refuses unless standard input and output are terminals. The check is on the
   file descriptors, not the environment. The refusal says approval is owner-run.
3. Option `--module <name>` approves one module only, still requiring the typed hash. It
   cannot approve a `harness` or `process` module by an earlier package record.
4. The command never writes outside the store, and never into the package directory. It
   refuses a package given as a symbolic link, as the verifier does.
5. Tests drive the command through a pseudo-terminal pair so the terminal check is real, and
   cover: wrong text records nothing; correct text records; piped input is refused; a
   package that fails verification records nothing; a module changed between the request
   and the answer records nothing, because the hashes are taken again just before writing.

Verification: the tests pass, and the documented sample run approves the fixture package in
a temporary store and `verify` is unchanged.
Completion: only a typed confirmation on a terminal records an approval, and it binds to
hashes taken at the moment of writing.
Review: independent review including the security reviewer.

### Increment H — Inert download

Dependencies: A
Affected areas: `workbench/fetch.py`, `tests/test_fetch.py`, `docs/development.md`

1. `fetch(store, source, ref)` creates a fresh directory under the store's `cache/` and
   fetches the ref into a bare repository there with `core.hooksPath` pointed at an empty
   directory, `GIT_*` variables scrubbed, no tags, no submodule recursion, no prompt, and a
   timeout. It resolves the ref to a full commit hash.
2. It lists the tree with `git ls-tree -r -z` and refuses the whole download on any entry
   that is not a regular file (modes 100644 and 100755 only), any path the path validator
   rejects, any single file or total size over a limit, or more files than a limit. Limits
   are constants with stated values, 16 MiB per file as in the contract, 64 MiB total and
   2048 files, for the owner to adjust at approval.
3. It reads each blob with `git cat-file` and writes it under a second fresh directory
   (`cache/<key>/package/`) with the safe write layer, preserving only the owner execute
   bit. It then deletes the bare repository, so the cache holds data only. Nothing runs and
   no checkout occurs.
4. On any failure, nothing is left in the cache. A cache directory is never reused: a second
   fetch of the same ref makes a new directory.
5. Tests use a repository created in a temporary directory with `file://`: a good package;
   a symbolic link entry; a submodule entry; a `.git` path; a path with `..` made through a
   crafted tree; an oversize file; too many files; a ref that moves between two fetches; and a
   repository with a `post-checkout` hook and an attributes filter that would run on
   checkout, and the test shows neither ran. The tests use no network.

Verification: the tests pass; a search shows the module never calls checkout, clone with
working tree, or any shell.
Completion: a hostile repository either yields inert data in the cache or yields nothing.
Review: independent review including the security reviewer.
Sensitive action: the module can reach the network when given a remote URL. It is not
exercised against a real remote by any test or by this plan's verification.

### Increment I — Approve from a source, and the pin

Dependencies: G, H
Affected areas: `workbench/approve.py`, `workbench/cli.py`, `workbench/approvals.py`,
`tests/test_approve.py`, `docs/development.md`

1. `approve --source <url-or-path> --ref <ref>` runs `fetch`, verifies the cached copy, and
   shows the request from the cached copy, as the spec requires. The typed hash is the tree
   hash of that copy.
2. On approval, the package record also stores the resolved commit and the package tree hash.
   `check_package` accepts a package only when its tree hash equals the pinned one, so a ref
   that has since moved to different content is not approved.
3. A fetch that fails, or a cached copy that fails verification, ends with nothing recorded.
   The cache copy is kept when the owner declines, so the request can be read again. This
   plan adds no deletion; removing cache copies is deferred.
4. Tests: a source approved, then the ref moved to new content, then the new content is not
   approved while the pinned commit's content still is; a source whose cached copy fails
   verification records nothing; declining records nothing and leaves the cache.

Verification: the tests pass and the sample flow in `docs/development.md` runs against a
local repository.
Completion: the first approval pins the resolved commit and tree hash, and later checks
verify against it.
Review: independent review.

### Increment J — Pins and the launcher

Dependencies: A
Affected areas: `workbench/pins.py`, `workbench/launch.py`, `workbench/cli.py`,
`tests/test_pins.py`, `tests/test_launch.py`, `docs/development.md`

1. `pins.py` stores, per opaque project ID, a map from a helper's name to a pin: the
   helper's path relative to the project root and its expected SHA-256, in
   `projects/<id>/pins`. The path is checked with the path validator, so it is relative,
   has no `..` and names no `.git`. It is relative because clones of one project sit at
   different absolute paths. Reading is strict and fail-closed; writing is atomic and done
   only by an owner-run command, `python3 -m workbench pin <id> <name> <helper-path>
   --root <project-dir>`, which needs a terminal in the same way as `approve`. The command
   refuses a helper that is not inside the root, is a symbolic link or is not a regular
   file, and records the path relative to the root.
2. `launch.py`: `launch <id> <name> --root <project-dir> -- <args>` takes the helper's
   location only from the pin: it reads `<root>/<pinned path>` through the safe reader, with
   the root a real directory and no symbolic link on the way, hashes the bytes, compares
   with the pinned hash, writes those exact bytes to a new file in `bin/run/` with mode
   `0700`, and executes that file with the arguments, no shell. The caller cannot name a
   different path. A missing pin, a missing or unreadable helper, a symbolic link, a path
   outside the root or a hash difference runs nothing and exits 1 with the reason. The copy
   is removed after the run.
3. Store initialization writes `bin/wb`, a short POSIX shell script that runs `python3 -m
   workbench "$@"` with the distribution's directory on `PYTHONPATH`. Its content is fixed
   text apart from that one absolute path, and a test fixes it byte for byte. The name `wb`
   is kept as the specs state it. Initialization looks for another `wb` on `PATH` and, if
   it finds one that is not this wrapper, prints a warning naming it. The warning never
   stops a command and nothing is put on `PATH` by the workbench.
4. Tests: a helper that matches its pin runs; one edited after pinning does not; one replaced
   between the hash and the run still runs the verified bytes; a helper that is a symbolic
   link or a FIFO is refused; a pinned path that is moved, removed or points outside the
   root is refused; the same pin works from two clones at different absolute paths; the
   caller cannot substitute another path; a missing pin refuses; the pin command refuses without a
   terminal; `wb` is regenerated identically on a second initialization; a different `wb` earlier on
`PATH` (a fake executable in a temporary directory) produces the warning, and an absent one
does not.

Verification: the tests pass; the documented run executes a fixture helper and refuses an
edited copy.
Completion: a pulled edit to a pinned helper is not run until the owner re-pins it.
Review: independent review including the security reviewer.

### Increment K — Record the formats and the decisions

Dependencies: I, J
Affected areas: `docs/specs/trust-and-approval.md`, `docs/specs/repository-boundary.md`,
`docs/specs/module-contract.md`, `docs/decisions/` (proposed records),
`docs/roadmaps/workbench-v1.md`, this plan

1. Edit `trust-and-approval.md` in place so that the settings and record fields, the
   package record, the typed-confirmation rule, the inert-download rules and limits, and the
   launcher match what the code does. Remove or narrow the Deferred item for record formats
   and say which names stay proposals.
2. Edit `repository-boundary.md` for the exact store layout (`bin/`, `bin/run/`) and
   `module-contract.md` for the first-party rule (location plus shipped record). Record the
   gap that a module has no way yet to declare an added hard stop, and leave it to the
   owner to rule or defer.
3. Draft decision records with `Status: Proposed` only for choices that are durable and not
   already decided: that the store location is not configurable, and that first-party status
   is by location plus shipped record. Accepting them is the owner's act, and this plan
   completes only when the owner has accepted or declined each.
4. Update the roadmap's current state; do not mark the candidate complete.
5. Fill in this plan's Result, including the acceptance criteria not reached.

Verification: a reading of the specs against the code and fixtures shows no field or rule the
code applies that the spec omits, and the reverse.
Completion: the spec edits exist and the owner has ruled on each proposed decision.
Review: independent review of the spec edits only if the owner asks.

## Verification

- `python3 -B -W error -m unittest discover -s tests` passes in full, from a fresh clone.
- `python3 -m workbench approve` approves the fixture package only on a terminal with the
  correct typed text, and `launch` runs a pinned fixture helper and refuses an edited one,
  as `docs/development.md` states.
- Every test named in the completion criteria exists; the Result maps each to its file.
- The store, record, fetch and launch tests each leave the real home directory untouched,
  because every one uses a temporary root; a test asserts the real store path is not opened.
- `git diff --check` is clean, and no file outside the enumerated areas changed.

## Risks and sensitive actions

- **This plan is large.** Eleven increments, two of them with network or process-execution
  surface. The limit in `docs/plans/README.md` is fifteen. The owner ruled on 2026-10-20
  that the plan is not split, so it stays one plan with one roadmap candidate.
- **The store is the root of trust and shares the owner's account.** Anything that can write
  it can forge an approval. Mitigation here: no configurable location, strict ownership and
  mode checks, no-follow access, a terminal-only approval command. Real enforcement is the
  deny rule `claude-harness` renders; until then the store is protected by instruction and
  `docs/development.md` says so.
- **Typed confirmation is not authentication.** An agent holding a pseudo-terminal could type
  it. The plan treats the terminal check as friction, not as the barrier, and tests only that
  a plain pipe is refused.
- **Fetching hostile git content.** Git has had flaws in hook handling, filters, submodules
  and path rewriting. Mitigation: no checkout, hooks disabled, objects read directly, a
  closed set of modes, the path validator on every entry, size limits, and the security
  reviewer on Increment H. A git flaw in object parsing itself is outside this plan.
- **The launcher executes code.** It runs a helper the owner pinned. Mitigation: hash the
  bytes once and execute those bytes from a private directory, no shell, and refuse
  anything but a regular file. It does not sandbox the helper.
- **Formats fixed too early.** Approvals bind to the record formats and the key
  derivation. Nothing is approved yet in the wild, so a change costs only tests, but a
  second change after the owner starts approving would invalidate real records.
  Mitigation: Increment K shows the formats before anything depends on them.
- **First-party rule is a call.** Location plus shipped record is simple and has no key to
  manage, and it trusts the install directory. A different rule needs a decision record.
- **Settings are written on first use.** The first command creates files in the owner's
  home directory. The plan states this, tests run only on temporary roots, and the manual
  verification in Increment A is the one run that creates the real store.
- Sensitive actions: Increment A's manual verification creates `~/.config/project-workbench/`
  once. Increment H can reach the network and is never run against a real remote by this plan.
  No dependency is installed, no secret is used, nothing is deleted, and nothing is pushed or
  published.

## Review record

Reviewed by Codex (model `gpt-5.6-luna`, medium effort) on 2026-10-20, at the owner's
request, while the plan was `Proposed`. One round of the three allowed was run; the owner
approved the plan after it. The review is not closed.

- **R1-F1** (blocker): `launch` had no way to find the helper to hash and run. Applied: the
  pin stores the helper's path relative to the project root, `launch` takes the location
  only from the pin, and tests cover moves, escapes, two clones and substitution.

## Deferred work

- Plan approval, delegated approval and the delegation helper (`code-work-module`).
- Acknowledgement baselines and their diffs (`base-and-manifests` and later).
- Rendering the floor and the store deny rule into a harness, and the `allow` validator for
  the neutral rule list (`claude-harness`).
- How a module declares an added hard stop (a `module-contract` change, ruled in Increment K).
- Removing a cached download, and pruning old cache directories.
- The project ID, the entry's first-seen remote check and the manifest pin
  (`base-and-manifests`).
- Packaging and installing the workbench itself, which `wb` assumes.
- Windows support.

## Result

Not started.
