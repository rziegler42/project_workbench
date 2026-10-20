# Base, manifests and installing into a new target

Status: Completed
Created: 2026-10-20
Candidate: workbench-v1#base-and-manifests
Specs: installer-interface, repository-boundary, module-contract, trust-and-approval

## Goal

Build `wb preview install` and `wb install`, so the workbench can create a project from a
chosen set of approved modules in a new target directory, as `installer-interface.md`
specifies. The install writes the base, the modules' committed files, the project seed and ID,
the committed manifest and `.workbench/.gitignore`, and the project's entries in the guarded
store. It shows the owner a preview first, and writes nothing until the owner has typed the
preview's digest in a terminal. It commits nothing and writes no harness file.

When this plan is done a test installs a fixture package into a temporary target and checks
every file, the manifest and the store entries; a hostile target, a swapped target and a
changed package are each refused with nothing written; and the specs record the formats that
were built. Attach, upgrade, add-a-module, check and the local manifest are not built.

## Scope

- **The target:** choosing it from its two spellings, the symbolic-link refusal, the single
  resolution to a held no-follow descriptor with its identity, the refused places, and the
  classification of a target as new or existing from its files, without git
  (`installer-interface.md`, "The target" and "States of a target").
- **A project writer** that creates files exclusively, one path component at a time, from the
  held target descriptor, and creates a missing target inside its held parent.
- **The committed manifest:** its concrete format, a canonical serializer and a strict reader,
  the project seed and the project ID.
- **The base:** its content, where it lives in the distribution, and the base-owned slots that
  `module-contract.md` left to this candidate, taught to the verifier.
- **A snapshot of each selected module** read once into memory, proved to reproduce the
  verified hashes, and used as the only source of bytes to write.
- **The write plan:** every path, owner class, mode and byte, the slot blocks, the manifest,
  the store writes and the `git init`, the injective digest over all of it, and the preview
  text.
- **`wb preview install`:** read-only, no network, reads the approved cache and local package
  directories only.
- **`wb install`:** owner-run and terminal-only; the typed digest; the writing order; the
  `.workbench/local/incomplete` marker; exit 3 and the report after a failure part-way; the
  top-level interrupt handler.
- **The project's store entry:** `projects/<id>/` with the first-seen record and the
  acknowledgement baselines for the files written.
- **Documents:** the formats and rules in the specs, the command table in
  `docs/development.md`, the roadmap's current state, and decision records for the durable
  choices (as `Proposed`).

## Non-goals

- Attach, the local manifest, the per-clone harness files and the `.git/info/exclude`
  entries. Install requires, verifies and gates a harness module and then stops short of
  attach (Question 2).
- `upgrade`, adding a module, `check`, and the acknowledgement *check* and diff. The
  baselines are written; nothing reads them yet.
- Owner classes beyond recording one per file, and any rule about slots on upgrade
  (`ownership-and-upgrade`).
- A rule or a field that lets a module choose its files' owner class; this plan uses a fixed
  mapping (My calls, 3).
- Any git command other than `git init` in a target that has no `.git`, and any use of an
  existing `.git`'s configuration. No command commits, pushes or publishes.
- Renaming the usage text from `python3 -m workbench` to `wb`; the new commands' text says
  `wb` and the old commands keep theirs, as the interface spec records.
- Windows, a machine-readable output form, and checking that a target is owned by the current
  user or is not a mount point (all deferred by the interface spec).

## Assumptions and constraints

- **Discovery:** skipped. This project provides no discovery tooling. The scope was checked
  directly against `workbench/safefs.py`, `workbench/cli.py`, `workbench/gate.py`,
  `workbench/store.py`, the four specs above and the roadmap candidate.
- **Same stack:** Python 3, standard library only, `unittest`, the layout of the earlier
  candidates. No dependency is added. Every filesystem read and write goes through the safe
  layer or the new writer, which is built on the same no-follow, descriptor-relative calls.
- **The interface spec is approved and is not reopened.** Its rules (target rules 1 to 10,
  the states table, the preview and approval rules, the digest, the output prefixes, the exit
  codes, the failure rule and the marker) are built as written. Where this plan finds a gap or
  a conflict it is a numbered question for the owner, with a recommended answer. Approving
  this plan with those answers adopts them, and Increment A writes them into the specs;
  answers the owner changes are written as changed.
- **The snapshot rule (`gate.py`):** the gate approves what `verify` hashed. So the install
  reads each module's files once, hashes those exact bytes, requires the declaration hash and
  tree hash to equal the verified and approved ones, and writes only those bytes. Nothing is
  read from the cache or the package again after that.
- **Trust in the base:** the base is part of the workbench distribution and is trusted as the
  workbench code is (`trust-and-approval.md`, the distribution is the trust root). It is not a
  module and has no approval record. Its tree hash and the workbench version are recorded in
  the manifest.
- **The manifest is untrusted text** when read later (`installer-interface.md`, "Rules common
  to the project commands"). This plan writes it and reads it back only in tests; no command
  here acts on an existing manifest.
- **Tests never touch the real store or the network.** They pass a temporary store root, build
  packages and `file://` repositories in temporary directories, and drive the terminal with
  `tests/support.drive_pty`.
- **The suite today** has 657 tests, all passing, and must still pass after every increment.

### Points for the owner to settle at approval

Each has a recommended answer. Question 1 blocks: without an answer the install produces a
directory that every other project command then refuses.

1. **Who creates `.git`? (blocking.)** The states table makes a missing or empty target "new"
   and requires a real `.git` directory for "existing", but no document says what makes it.
   *Recommended:* `install` runs `git init` itself, only when the target has no `.git`, never
   in a target that already has one (a lone `.git` is used as it is, and its configuration is
   never read), with the same scrubbed environment and empty template directory that `fetch.py`
   uses, and with `--initial-branch=main`. The preview lists the `git init` as an action and
   the digest covers it.
2. **The harness step.** The roadmap candidate says "without a harness step yet"; the
   interface spec says install requires exactly one harness module and ends with attach.
   *Recommended:* require, verify and gate the harness module as the spec says, write nothing
   for it (it adds nothing to the committed tree or the manifest, which never names a
   harness), skip attach, and print `harness not attached: attach is not built yet`. The
   `--no-harness-required` option stays off `install`. `claude-harness` adds the attach step
   to this command.
3. **Local package directories in `preview`.** `preview` reads only the approved cache, but
   `approve` of a local directory does not cache it. *Recommended:* `preview` and `install`
   accept a local directory as a `--package` source. Reading a local directory contacts no
   network and writes nothing, the gate still requires its exact declaration and tree hashes
   to be approved, and the snapshot rule covers a swap. A URL source for `preview` must have
   been fetched by `approve`, and `preview` refuses and names one that was not.
4. **Several packages and refs.** *Recommended:* `--package <source>` may repeat; a `--ref
   <ref>` binds to the nearest `--package` before it and may appear at most once per package;
   `--select` names modules as `verify` does (`<module>` or `<package>/<module>`). The parser
   reads these in order by hand, since `argparse` cannot associate them.
5. **Acknowledgement baselines.** The interface spec has install write baselines for the files
   in its preview; they are not built. *Recommended:* in scope, write only. The format is one
   file, `projects/<id>/baselines`, strict JSON mapping each path to the SHA-256 of the bytes
   written. Reading, diffing and acknowledging are `ownership-and-upgrade` and later.
6. **The first-seen record.** The spec records a canonical remote URL, or the path when there
   is no remote. Reading a remote needs `.git/config`, which is hostile input. *Recommended:*
   install records the resolved path, with a `kind` of `path`; a freshly initialized
   repository has no remote. Recording and comparing a remote is settled by the candidate
   that first meets a project in a second clone (`claude-harness`, at attach). When the target
   was a lone `.git`, install warns that no remote was recorded.

### My calls to confirm

These are the author's choices, not the owner's, and Increment A states each in the specs.

1. **Filled slot syntax.** A filled slot keeps its marker. The file holds, in install order,
   one `BEGIN <package>/<module> slot:<name>` … `END` block per filler, then the
   `<!-- @slot: <name> -->` marker line, so a later module can add its block and the
   append-only interface holds. A fill source that contains a marker line of its own is
   refused.
2. **Base-owned slots:** `policy` (in `AGENTS.md`) and `docs-index` (in `docs/README.md`),
   the two that `groundwork.md` and `code-work.md` already name. A module that declares it
   owns either is refused, because a slot has one owner.
3. **Owner classes at install:** the base's `AGENTS.md` and `docs/README.md` are `seeded`;
   `.workbench/.gitignore` is `module-owned` (base-owned); a module's namespace files under
   `.workbench/<package>/<module>/` are `module-owned`; a file written from `writes` is
   `seeded`; a filled block is `slot block`. `ownership-and-upgrade` may add a declaration
   field for the choice.
4. **A module's namespace holds a copy of the whole module tree** (declaration, `templates/`,
   `files/` and the rest), because a template "stays in its module" and is used at creation
   time. A harness module is the exception: it writes nothing committed.
5. **A harness module that declares `writes` or `fills` is refused at install:** its files
   are per-clone and a committed file would name the harness.
6. **The seed** is a random UUID4 string from `uuid`; the project ID is its SHA-256 as 64
   lowercase hex digits, as `repository-boundary.md` says.

## Completion criteria

- `wb preview install` and `wb install` exist and match `installer-interface.md` for every
  rule they reach; each reachable rule has a named passing test.
- A test installs a fixture package into a missing target, an empty directory and a lone
  `.git`, and checks every written path, its bytes, its mode and its recorded owner class,
  the manifest, `.workbench/.gitignore`, the store's `projects/<id>/` entries, and that
  `git ls-files` lists nothing the install did not write and the install committed nothing.
- The manifest is byte-identical for two installs that differ only in where they run, apart
  from the seed; contains no timestamp or per-clone value; and never names a harness.
- Each refusal in the target rules and states table is tested and writes nothing: two
  differing spellings, a symbolic-link target, the root, the home directory, the store, a
  directory containing the store, a missing parent, a file, a directory with other content, a
  `.git` that is a file or a link, and a `.workbench` that is a link.
- A package changed after the preview, a target swapped for another directory after the
  preview, a wrong typed digest, input typed ahead, and a missing terminal each refuse, write
  nothing, and exit 1 as the spec says.
- An unapproved module, a refused verification and a source that `preview` has no approved
  cache of each refuse before any preview is shown.
- A failure injected after the first write exits 3, lists what was written and not, leaves
  `.workbench/local/incomplete` in place, and that directory is then classified as not an
  existing project.
- A hostile `.git/config` in a lone-`.git` target is never read or run by `preview` or
  `install`.
- The base-owned slots work in the verifier: a fill of `policy` or `docs-index` with no
  declared owner no longer warns, and a module that owns either is refused.
- `docs/development.md`, the specs and the roadmap record what was built; the decision
  records exist as `Proposed`.
- The full suite passes, `git diff --check` is clean, and an independent security review of
  Increments B, C and I has no unresolved finding when the owner asks for one.

## Increments

### Increment A — Record the answers and settle the formats in the specs

Dependencies: the owner's answers to the questions above
Affected areas: `docs/specs/installer-interface.md`, `docs/specs/repository-boundary.md`,
`docs/specs/module-contract.md`, `docs/specs/trust-and-approval.md`, `docs/decisions/` and
its index

Outcome: the specs say what will be built, so the code is written against text and not
invented while coding. Documents only.

1. In `installer-interface.md`, write the owner's answers: who runs `git init` and how, the
   install's end without attach, local directories in `preview`, the `--package`/`--ref`
   spelling, and the first-seen record. Mark each as built-or-proposed as that file does.
2. In `repository-boundary.md`, write the concrete committed-manifest format (below), the
   filled-slot syntax with the retained marker, the owner classes at install, the contents of
   the base, and the formats of `projects/<id>/seen` and `projects/<id>/baselines`. Update
   "Layout" and the "not built yet" note.
3. In `module-contract.md`, name the base-owned slots in place of the deferral, and add the
   rule that a harness module declares no `writes` or `fills`.
4. In `trust-and-approval.md`, record the baselines format and that install writes them.
5. Draft decision records, `Proposed`, for the durable choices: the base ships in the
   distribution and is trusted as the workbench is; `install` creates `.git` itself; a
   harness module writes nothing committed. Add them to the decisions index.

**The manifest format (proposed here, recorded by this increment).** `.workbench/manifest.json`
is UTF-8 JSON with a final newline. Top-level keys are sorted: `base`, `files`, `packages`,
`seed`, `version`, `workbench`. `version` is the schema version, 1. `base` is the base's tree
hash. `workbench` is the installing workbench's version. `packages` is a list, one object per
line, sorted by name, each with `name`, `source`, `ref`, `commit` and `tree`, and `modules`
(sorted objects with `name`, `version`, `declaration` and `tree`). `files` is a list, one
object per line, sorted by path, each with `class`, `hash`, `path`, and for a block `slot`
and `block`. A harness package's harness module is omitted (a package that holds only the
harness is omitted whole). The serializer, not `json.dumps`, writes the layout, so the
one-entry-per-line shape does not depend on a library's formatting.

Verification: each rule the later increments build appears once in the specs; no spec
contradicts another (a search of the four specs for "attach", "first seen", "baseline",
"slot" and "manifest" finds no conflict); the decision records are `Proposed`; the spec cites
no path under `.debug/`.

Evidence: the changed specs, the new records, and the search output.

### Increment B — The target: choosing, resolving and classifying

Dependencies: Increment A
Affected areas: `workbench/target.py` (new), `tests/test_target.py` (new)

Outcome: one module decides, from a spelling, which directory a project command works on and
what state it is in, and holds it open.

Interfaces (Produces):

```python
class TargetError(Exception):          # a refusal; the message names the place
class TargetUsage(TargetError):        # exit 2: empty or differing spellings

def choose(positional, dir_option) -> str
def open_target(spelling, store_root, home=None) -> Target
class Target:        # context manager; holds descriptors
    path: str                # resolved absolute path
    state: str               # "new-missing", "new-empty", "new-git", "existing"
    fd: int                  # the held directory; for "new-missing" the held parent
    name: str                # for "new-missing", the name to create in the parent
    def recheck(self) -> None          # raises TargetError if identity changed
    def has_incomplete_marker(self) -> bool
```

1. `choose`: an empty string is a usage error; both spellings must name the same directory by
   file identity (resolved path when neither exists), else `TargetUsage`; the default is `.`.
2. `open_target`, in rule order: inspect the spelling (strip trailing separators and `.`
   components, refuse a final component that is a symbolic link, to a directory or nowhere);
   resolve once; open with `safefs.open_root`-style no-follow flags and keep device and inode;
   compare against the refused places by identity — root, the home directory from `HOME` and
   from the account database, the store and anything inside it, anything containing it;
   classify.
3. Classification reads files only, never runs git, and uses no-follow `stat` throughout. The
   states table: missing with an existing parent; empty; only a real `.git` directory; its own
   real `.git` directory plus `.workbench` and `.workbench/local` real directories and a
   regular-file `.workbench/manifest.json`; anything else refused. A missing parent, a file
   and `.workbench/local/incomplete` present (not an existing project) are refused with the
   state named.
4. `recheck` compares the held descriptor and the path again; the command calls it before the
   first write and after the approval.

Tests (names; each asserts the refusal text names the place and that nothing was created):
`test_choose_default_is_dot`, `test_choose_empty_is_usage_error`,
`test_choose_differing_spellings_refused`, `test_choose_same_directory_by_identity`,
`test_final_symlink_refused_even_to_directory`, `test_parent_symlink_is_resolved`,
`test_refuses_root_home_store_inside_store_and_container_of_store`,
`test_home_from_account_database_also_refused`, `test_state_missing_with_parent_is_new`,
`test_state_missing_parent_refused`, `test_state_empty_and_lone_git_are_new`,
`test_git_file_or_link_refused`, `test_existing_needs_manifest_regular_file`,
`test_workbench_link_is_not_existing`, `test_incomplete_marker_is_not_existing`,
`test_hostile_git_config_is_never_read`, `test_recheck_detects_swapped_directory`,
`test_case_variant_of_store_refused_on_case_insensitive_volume` (skipped where the volume is
case-sensitive).

Verification: `python3 -B -W error -m unittest discover -s tests -p 'test_target.py'`, then
the full suite.

Evidence: the passing tests and the module.

### Increment C — The project writer

Dependencies: Increment B
Affected areas: `workbench/projectfs.py` (new), `tests/test_projectfs.py` (new)

Outcome: a writer that can only create files exclusively, inside the held target, one
component at a time, and can make the missing target in its held parent.

Interfaces (Produces):

```python
class WriteConflict(safefs.SafeFsError):   # the path exists, or a link is in the way
class Writer:
    def __init__(self, target: Target)
    written: list[str]                    # relative paths created so far, in order
    def make_target(self) -> None         # for "new-missing": mkdir in the held parent
    def create_dir(self, rel: str) -> None
    def create_file(self, rel: str, data: bytes, executable: bool = False) -> None
    def remove_marker(self) -> None       # unlinks .workbench/local/incomplete only
```

1. Every path goes through `safefs.validate_relpath`; the full set of paths of a write is
   also checked for case and normalization collisions with `safefs.check_tree_paths` by the
   caller before the first write.
2. `create_file` walks from the held descriptor one component at a time, each directory opened
   with `O_NOFOLLOW | O_DIRECTORY`; parents are created through the held descriptor; the file
   is created with `O_CREAT | O_EXCL | O_NOFOLLOW`; an existing path of any kind, or a link at
   any component, raises `WriteConflict`. The file is written in full, `fsync`ed, and given
   mode 0755 only when `executable`. Nothing is overwritten and nothing is unlinked except
   the marker.
3. `make_target` calls `Target.recheck()` first and creates the directory with the mode the
   process umask gives; the new directory's descriptor becomes the held target.

Tests: `test_creates_file_exclusively_and_records_it`,
`test_existing_file_is_a_conflict_not_overwritten`,
`test_symlink_at_any_component_is_a_conflict` (file, parent, `.workbench`, `.workbench/local`),
`test_parent_swapped_for_link_after_check_does_not_escape` (using the `safefs._hook` seam),
`test_executable_bit_only_when_asked`, `test_make_target_inside_held_parent`,
`test_make_target_refused_when_parent_swapped`, `test_remove_marker_only_removes_the_marker`,
`test_failed_write_leaves_earlier_files_and_lists_them`.

Verification: the file's tests, then the full suite.

Evidence: the passing tests; the module docstring records the limits (no atomic multi-file
write; a kill can leave a part-written file, which the marker covers).

### Increment D — The canonical manifest, the seed and the project ID

Dependencies: Increment A
Affected areas: `workbench/manifest.py` (new), `tests/test_manifest.py` (new)

Outcome: the manifest has one serializer and one strict reader, so two installs with the same
content write the same bytes.

Interfaces (Produces):

```python
class ManifestError(Exception)
def new_seed() -> str                               # uuid4 string
def project_id(seed: str) -> str                    # sha256 hex of the seed, 64 digits
def serialize(document: dict) -> bytes              # the layout recorded in Increment A
def parse(data: bytes) -> dict                      # strict; raises ManifestError
BASE_IGNORE = b"/local/\n"                          # the content of .workbench/.gitignore
```

1. `serialize` writes exactly the layout Increment A records and refuses a document that is
   not already sorted and shaped (unknown keys, a harness entry, a timestamp-like field).
2. `parse` reuses the strict loader that `declarations.py` uses (duplicate keys, NaN, floats,
   depth and size limits), then checks the shape and that `serialize(parse(x)) == x`, so a
   manifest that is not in canonical form is refused.
3. `project_id` agrees with the store's accepted form (64 lowercase hex digits).

Tests: `test_known_answer_manifest_bytes` (a fixed document and its exact bytes and SHA-256),
`test_one_entry_per_line`, `test_serialize_refuses_unsorted_input`,
`test_parse_round_trip`, `test_parse_refuses_noncanonical_bytes`,
`test_parse_refuses_duplicate_key_unknown_key_float_and_depth`,
`test_no_harness_or_timestamp_field_allowed`, `test_project_id_is_sha256_of_seed`,
`test_two_seeds_give_different_ids`.

Verification: the file's tests, then the full suite.

Evidence: the known-answer test and the module.

### Increment E — The base and the base-owned slots

Dependencies: Increment A
Affected areas: `base/` (new, in the distribution), `workbench/base.py` (new),
`workbench/verify.py`, `tests/test_base.py` (new), `tests/test_verify.py`

Outcome: the base content exists, is read safely and hashed, and the verifier knows the slots
it owns.

Interfaces (Produces):

```python
BASE_SLOTS = ("docs-index", "policy")
class BaseError(safefs.SafeFsError)
Base = collections.namedtuple("Base", "files tree_hash")   # files: {rel: bytes}
def load_base(distribution=None) -> Base
```

1. `base/` holds `AGENTS.md` (project policy headings and the `policy` slot marker),
   `docs/README.md` (the `docs-index` slot marker), and `.workbench/.gitignore` is generated
   from `manifest.BASE_IGNORE`, not stored twice. Content is short, tool-neutral, and
   contains no harness file name.
2. `load_base` reads every file through the safe reader from `<distribution>/base`, refuses a
   link, a non-regular file or a path that fails the validator, and returns the bytes and the
   tree hash.
3. `verify.py` treats a fill of a base-owned slot as owned: no warning. A module whose
   `slots` names a base-owned slot is refused (a slot has one owner). Both are covered by new
   cases in `tests/test_verify.py`; no existing verifier test changes.

Tests: `test_load_base_hashes_files`, `test_base_refuses_link_and_special_files`,
`test_base_contains_no_harness_file_name`, `test_base_slot_markers_present_exactly_once`,
`test_fill_of_base_slot_does_not_warn`, `test_module_owning_a_base_slot_refused`.

Verification: the new tests and `test_verify.py`, then the full suite.

Evidence: the base files, the passing tests, and a note in `docs/development.md` for the
`base/` directory (finished in Increment J).

### Increment F — A snapshot of each selected module

Dependencies: Increment A
Affected areas: `workbench/hashing.py`, `workbench/snapshot.py` (new),
`tests/test_hashing.py`, `tests/test_snapshot.py` (new)

Outcome: the bytes the install will write are read once and proved to be the bytes that were
verified and approved.

Interfaces:

```python
# hashing.py (Produces; hash_tree is refactored to call it, with identical results)
def tree_hash_of(files: dict, executable: set) -> str
# snapshot.py (Produces)
class SnapshotError(safefs.SafeFsError)
Snapshot = collections.namedtuple("Snapshot", "package module files executable")
def take(module_root: str, verified) -> Snapshot
```

1. `tree_hash_of` is the existing tree-hash rule over an in-memory map. `hash_tree` keeps its
   results; the known-answer tests are unchanged and a new one shows the two functions agree.
2. `take` reads every file of the module directory once through the safe reader, with the
   identity taken at listing, computes `tree_hash_of`, and refuses unless it equals the
   verified tree hash. It also re-parses `module.json` from those bytes and refuses unless the
   declaration hash equals the verified one.
3. The caller verifies and gates the selection first, then takes snapshots; nothing reads the
   package again afterwards.

Tests: `test_tree_hash_of_matches_hash_tree`, `test_take_returns_verified_bytes`,
`test_take_refuses_file_changed_after_verify`, `test_take_refuses_added_file`,
`test_take_refuses_changed_declaration`, `test_take_refuses_link_and_special_file`.

Verification: the two test files, `test_hashing.py` known answers unchanged, then the full
suite.

Evidence: the passing tests.

### Increment G — The write plan, its digest and the preview text

Dependencies: Increments B, D, E and F
Affected areas: `workbench/installplan.py` (new), `tests/test_installplan.py` (new)

Outcome: one pure function builds everything an install would do, the digest over it, and the
preview text. `preview` and `install` both call it, so they cannot differ.

Interfaces (Produces):

```python
Action = collections.namedtuple("Action", "kind path owner_class mode size hash detail")
Plan = collections.namedtuple("Plan", "target_identity actions manifest seed project_id "
                                      "store_writes git_init digest")
class PlanError(Exception)
def build(target, selection, snapshots, base, seed, workbench_version) -> Plan
def digest_of(plan_fields) -> str            # full SHA-256 hex
def render(plan, target_path) -> str         # the preview text; ASCII-cleaned
```

1. `build` assembles, in the spec's order, the files: base files (slot markers replaced by
   filled blocks and the retained marker), each non-harness module's namespace copy, each
   `writes` file, and the manifest and `.workbench/.gitignore`; the directories; the
   `git init` action when the target has no `.git`; and the store writes (`projects/<id>/`,
   `seen`, `baselines`). The actions are ordered with making a missing target first, then
   `.workbench/local/incomplete`, then `git init`, then everything else, so that nothing is
   written into the target before the marker exists.
2. Before returning it checks the whole path set with `safefs.check_tree_paths`, refuses a
   path two modules both write, a path a module writes that the base writes, a harness module
   that declares `writes` or `fills`, a fill whose slot has no marker in exactly one file, and
   a fill source containing a marker line.
3. `digest_of` is SHA-256 over an injective encoding: a JSON array with explicit field names,
   never a joined string. It covers the command and selection, the target's device and inode,
   the workbench version, every module's hashes, every path with its class, action, mode, size
   and content hash, every directory, the `git init`, the seed and project ID, and every store
   write. The seed and ID are generated before `build` and passed in.
4. `render` follows "What a preview shows": the resolved target first, a summary of counts, then
   each module and each path, every package-supplied string through `display.ascii_text`, a
   source URL with credentials and query removed, the digest in full only when asked for.
   Nothing is truncated.

Tests: `test_plan_order_and_markers`, `test_filled_slot_keeps_marker_and_orders_blocks`,
`test_two_modules_writing_one_path_refused`, `test_module_path_colliding_with_base_refused`,
`test_case_colliding_paths_refused`, `test_harness_with_writes_or_fills_refused`,
`test_fill_with_no_or_two_marker_files_refused`, `test_fill_source_containing_marker_refused`,
`test_digest_changes_with_any_byte_path_mode_class_or_store_write`,
`test_digest_encoding_is_injective` (the `"a b"+"create"` versus `"a"+"b create"` case),
`test_same_inputs_same_digest`, `test_render_shows_target_first_and_counts_before_detail`,
`test_render_escapes_lookalike_and_control_characters`,
`test_render_strips_url_credentials_and_query`.

Verification: the file's tests, then the full suite.

Evidence: the passing tests and a sample rendered preview recorded in the Result.

### Increment H — `wb preview install`

Dependencies: Increment G
Affected areas: `workbench/cli.py`, `workbench/sources.py` (new), `workbench/preview.py` (new),
`tests/test_preview.py` (new), `tests/test_cli.py`

Outcome: an agent can see exactly what an install would do, with no network and no write.

Interfaces (Produces):

```python
# sources.py
def parse_packages(argv_tail) -> list[tuple[str, str|None]]    # ordered (source, ref)
def resolve_cached(store, source, ref) -> str                  # a cache package/ path
# preview.py
def run(guarded, args, out, err, distribution) -> int
```

1. The parser reads `--package`/`--ref` in order and `--select`; a `--ref` with no preceding
   `--package`, a second `--ref` for one package, an empty value, or no `--select` is a usage
   error (exit 2, before the store is touched).
2. `resolve_cached` accepts a local directory as it is (not a symbolic link) and, for a URL,
   finds a cache entry whose `fetch.json` source and ref match and whose package record is
   approved; it never fetches, never creates a directory, and refuses and names a source that
   is not cached and approved.
3. `preview.run` runs target rules 1 to 10 without writing, verifies the selection as one
   install with a harness required, calls the gate, takes snapshots, builds the plan and
   prints `render`; it ends with `preview only: nothing was written`. A refusal exits 1 with
   `refused:` lines; a produced preview exits 0. The digest is not printed.
4. `preview` writes nothing, not even the store's cache. The guarded store is still ensured
   first, as every command does.

Tests: `test_preview_prints_plan_and_writes_nothing` (a snapshot of the target tree and the
store before and after, `.git/index` unchanged), `test_preview_never_contacts_the_network`
(a patched `fetch.fetch` that fails if called), `test_preview_refuses_uncached_url_and_names_it`,
`test_preview_accepts_local_directory_that_is_approved`, `test_preview_refuses_unapproved_module`,
`test_preview_refuses_selection_without_harness`, `test_preview_target_rules_refuse_and_write_nothing` (also asserts no fetch and no cache
directory),
`test_usage_errors_exit_2_without_touching_store`, `test_ref_binds_to_preceding_package`,
`test_preview_matches_install_plan` (completed in Increment I).

Verification: the new tests, `test_cli.py`, then the full suite.

Evidence: the passing tests and a recorded run against the sample package.

### Increment I — `wb install`

Dependencies: Increment H
Affected areas: `workbench/install.py` (new), `workbench/cli.py`, `workbench/fetch.py` (expose
the scrubbed environment), `tests/test_install.py` (new), `tests/test_cli.py`

Outcome: the owner can install into a new target from a terminal, after typing the digest.

Interfaces (Produces):

```python
def run(guarded, args, stdin, out, err, distribution) -> int
```

1. Refuse unless standard input and output are terminals, tested on the descriptors as
   `approve` does (share its helper rather than copy it), before anything is fetched. The
   message says to use `preview`.
2. Run the complete target checks first (rules 1 to 10: spellings, link refusal, resolution,
   refused places, state), so a refused target causes no fetch and no cache write. Then fetch
   each URL source into the inert cache (the only network use), verify the selection, gate
   it, take snapshots, build the plan, print the resolved target and the preview, then
   ask for the first 12 characters of the digest. Input is read after `termios.tcflush`,
   bounded in length, and compared to the digest held in the process. Anything else prints
   `cancelled: nothing was written` and exits 1.
3. After approval: call `Target.recheck()`, rebuild the digest from the same in-memory bytes
   and refuse if it differs, then write in this order: make the target if missing; create
   `.workbench/local/incomplete`; `git init` if there is no `.git` (scrubbed environment,
   empty template, `--initial-branch=main`, no configuration read); the base and module files
   in install order; the manifest and `.workbench/.gitignore`; the store's `projects/<id>/`
   with `seen` and `baselines`; then remove the marker. Print the count of paths and
   `nothing was committed`, and `harness not attached: attach is not built yet`.
4. Any exception after the first write stops at once: print `failed:` with the cause, then the
   paths written and not written, leave the marker, exit 3. Before the first write a
   `KeyboardInterrupt` prints `cancelled:` and exits 130; a broken pipe ends quietly. Neither
   produces a traceback.
5. A failure to write the store's entries after the files are written is a failure part-way
   (exit 3), because the project then exists without its store entry; the report says so.

Tests: `test_install_into_missing_empty_and_lone_git_target`,
`test_install_writes_expected_tree_modes_classes_and_manifest`,
`test_install_runs_git_init_only_when_no_git`, `test_install_never_reads_lone_git_config`,
`test_marker_exists_before_git_init`, `test_failure_in_git_init_leaves_marker`,
`test_refused_target_causes_no_fetch_or_cache_write` (a patched `fetch.fetch` that fails if
called),
`test_install_commits_nothing`, `test_refuses_without_terminal_before_fetching`,
`test_wrong_digest_cancels_and_writes_nothing`, `test_typed_ahead_input_is_discarded`,
`test_package_changed_after_preview_refused`, `test_target_swapped_after_preview_refused`,
`test_existing_path_is_a_conflict_nothing_overwritten`,
`test_failure_after_first_write_exits_3_lists_paths_and_keeps_marker`,
`test_marker_directory_is_not_an_existing_project`,
`test_interrupt_before_write_exits_130`, `test_store_entries_written_and_id_matches_seed`,
`test_preview_matches_install_plan`, `test_install_end_to_end_from_file_url_source`.

Verification: the new tests, `test_cli.py`, then the full suite. The pseudo-terminal tests use
`tests/support.drive_pty` and a temporary `HOME`, never the real store.

Evidence: the passing tests and one recorded interactive run in a scratch directory.

### Increment J — Documents and the Result

Dependencies: Increment I
Affected areas: `docs/development.md`, `docs/specs/installer-interface.md`,
`docs/specs/repository-boundary.md`, `docs/specs/module-contract.md`,
`docs/roadmaps/workbench-v1.md`, `docs/decisions/` and its index, this plan's Result

Outcome: the documents say what exists.

1. In `docs/development.md`: the `preview install` and `install` commands in the command
   table, the preview and install section (what each reads and writes, the digest, the marker,
   exit codes), the `base/` directory, and the distribution layout.
2. In the specs, mark `preview install` and `install` as built, and change any "proposed" or
   "not built yet" wording that is now untrue. Record the options that were settled.
3. Update the roadmap's current state for this candidate without recording completion
   (completion is derived from this plan).
4. Check the decision records drafted in Increment A against what was built; edit a `Proposed`
   record if the build differed. The owner accepts them.
5. Fill in the Result: commits, test count, the sample preview, unresolved items.

Verification: a search of the documents for "not built" and "proposed" finds no statement
that is now false; `git status --short` shows only the intended files; the full suite passes.

Evidence: the changed documents and the search output.

## Verification

- `python3 -B -W error -m unittest discover -s tests` passes after every increment, and the
  count rises by the new tests only (657 before this plan).
- `git diff --check` is clean, and `git status --short` shows only files the increment names,
  with nothing under `.debug/`, `.claude/` or `CLAUDE.md`.
- No test touches the real guarded store or the network (`tests/support.forbid_real_store`).
- A manual run in a scratch directory under the scratchpad: `preview install` against the
  sample package, then `install` typed in a terminal, then `git status` in the target to see
  an uncommitted tree, then a second `install` into the same target to see the refusal.
- Each increment's commit names only changes present in its diff and carries
  `Plan: 2026-10-20-base-and-manifests#<label>`.
- Increments B, C and I touch untrusted input, the filesystem and a subprocess. When the owner
  asks, they get an independent security review before the plan is completed; its findings
  are untrusted and are evaluated as review comments.

## Risks and sensitive actions

- **A hostile target.** A directory arriving by clone can hold a `.git/config` that runs a
  program, a `.workbench` link, a FIFO named `manifest.json`, or a link planted after the
  check. Mitigation: no git is run in an existing `.git`; every check is no-follow and
  descriptor-relative; identity is re-checked before the first write; a link is a conflict.
  Increments B, C and I carry named tests for each.
- **The one subprocess.** `git init` runs only in a target that has no `.git`, with the
  scrubbed environment and an empty template directory so a user's `init.templateDir` cannot
  plant hooks. It still reads the process's `PATH` for the `git` binary, as `fetch.py` does.
- **Package text becoming policy.** A fill block lands in `AGENTS.md`, which agents read. The
  preview shows each block's source and hash; the module was approved on its own record;
  a fill containing a marker line is refused so one block cannot forge another's boundary.
- **A preview that differs from the write.** Both use `installplan.build` and the same
  in-memory bytes, and the write recomputes the digest and refuses on any difference.
- **A half-written project.** A kill or power loss can leave a part-written tree. The marker
  makes the directory a refused state, and the report tells the owner to delete it by hand and
  install again.
- **Size.** Ten increments is under the limit of 15. If review shows Increments G to I are
  larger than one reviewable commit each, split them with `<label>-A` labels rather than
  renumbering.
- **Design ahead of the later candidates.** The manifest format, owner-class mapping and slot
  syntax are used by `ownership-and-upgrade` and `claude-harness`. They are recorded in the
  specs as proposals-now-built, and a later plan may revise them in place with the spec
  change.
- No commit, push, deployment, dependency installation, secret use or deletion is part of
  this plan beyond the commits the owner asks for.

## Review record

Requested by the owner. Reviewer: Codex through `ask-codex`, model `gpt-5.6-luna`, medium
effort, bound of 3 rounds. The plan was `Approved` before the review started.

**Round 1** (2026-10-20): outcome `changes_needed`, two major findings. Both were accepted as
correct by the author. Each changed an increment's steps, so the owner approved the edits
in session on 2026-10-20 ("go with your recommendation"), and they were then applied to
Increments G, H and I (`docs/plans/README.md`, "Approval and revision"). No second round was
run.

- R1-F1 (applied): Increment I runs `git init` before it creates
  `.workbench/local/incomplete`, but `git init` is itself a write into the target, and the
  interface spec says the marker is created before anything else install writes. A failure
  after `git init` would leave a `.git` and no marker. Proposed: in Increment I step 3 and in
  the write order of Increment G, create the marker immediately after making a missing target
  and before `git init`; add a test that a failure during or right after `git init` leaves
  the marker. (Dependencies unchanged; the lone-`.git` and empty-directory cases already
  hold the marker first.)
- R1-F2 (applied): Increment I step 2 fetches URL sources before it
  resolves and classifies the target, but target rule 10 puts the target checks before any
  source work, so a refused target could still cause a fetch and a cache write. Proposed: in
  Increment I step 2, run the complete target checks of rules 1 to 10 first, then fetch; add
  `test_refused_target_causes_no_fetch_or_cache_write` (a patched `fetch.fetch` that fails
  if called). Increment H already orders the target checks first; add the same assertion to
  its refusal test.

## Deferred work

- Attach, the local manifest, the per-clone harness files and the `.git/info/exclude` entries
  (`claude-harness`); the install then ends with attach.
- Upgrade, adding a module, `check`, the acknowledgement check and diff, and format
  migration (`ownership-and-upgrade` and later).
- Recording and comparing a project's remote in the first-seen record.
- A declaration field that lets a module choose the owner class of its files.
- A target-ownership and mount-point check, a machine-readable output form, and renaming the
  old commands' usage text to `wb`.
- Cleaning up cache copies, shipped records of earlier releases and `bin/run/` directories.

## Result

Increments A to J are done, each as one local commit with the trailer
`Plan: 2026-10-20-base-and-manifests#<label>`. Nothing is pushed.

| Increment | Commit | What it added |
|---|---|---|
| plan | `47dc677` | this plan, approved |
| A | `8841895` | the owner's answers and the formats in the specs; three `Proposed` decision records |
| B | `8961e1f` | `workbench/target.py`: choosing, resolving, classifying and holding a target |
| C | `f6ea39e` | `workbench/projectfs.py`: the no-follow project writer |
| D | `05fb0ad` | `workbench/manifest.py`: canonical manifest, seed, project ID |
| E | `79fe90e` | `base/`, `workbench/base.py`, the base-owned slots in `verify` |
| F | `7053471` | `workbench/snapshot.py` and `hashing.tree_hash_of`: module bytes proved against the verified hashes |
| G | `9f28855` | `workbench/installplan.py`: the write plan, its digest and the preview text |
| H | `b0285dc` | `workbench/sources.py`, `workbench/preview.py`, `wb preview install` |
| I | `dd4b32d` | `workbench/install.py`, `wb install`, and the fixes from the security review |
| J | this commit | the documents |

**Tests.** The suite went from 657 to 814 passing (`python3 -B -W error -m unittest discover
-s tests`), the count rising by the new tests only. `git diff --check` was clean at each commit.
No test touches the real guarded store or the network. A recorded run under a pseudo-terminal in
a scratch directory: `install` printed the plan, took the digest, wrote 17 paths and exited 0;
`git status` in the target showed `.workbench/`, `AGENTS.md` and `docs/` untracked; a second
`install` into it was refused as an existing project.

**Security review** (Increments B, C and I, asked for by the owner; the reviewer was a separate
agent that ran experiments in a scratch copy, and its findings were treated as untrusted and
checked). Findings and what was done:

- Medium: `git init` followed a symbolic link planted at `.git` after the check and wrote a
  repository into another directory (15 of 15 trials). Fixed by not running git: `Writer.create_git`
  makes `.git` with `mkdir` and writes a fixed skeleton through held descriptors; the skeleton's
  hash is in the digest. The second round found the symlink and rename-then-symlink attacks
  refused in 10 of 10 trials, and real git accepted the result.
- Low: `fetch.git_executable()` could return a relative path (now absolute); `public_source` could
  leak part of the user information when it held `#` or `?` (now reads the authority as git does,
  and `normalize_source` refuses `?` and `#` in an ssh authority); created files followed the
  umask (now 0644 and 0755, narrowed by the umask only).
- Not changed: a long plan can scroll the high-risk and `.git` warnings off screen before the
  digest prompt; `fetch.json` keeps the raw URL in the private store; git's stderr in a download
  error is not redacted; a process with its own pseudo-terminal passes the terminal guard, as
  the specs already accept.
- Not tested by the reviewer: races on ancestors of the target, non-UTF-8 argv, huge inputs.

**Deviations from the plan's text.**

- `Action` has a `data` field (the bytes to write), `Plan` has `state` and `modules`, and
  `Selection(modules, packages)` is a new type; `Target.identity` was added; `sources.Resolved`
  and the `Command(target, packages, select)` tuple carry what a command works from.
  `install.run` takes that `Command`, not raw arguments, and optional `seed`, `version` and `which`
  for tests. `fetch.git_environment`, `fetch.git_executable` and `sources.local_package` are public.
- The `.git` is written by the workbench and git is not run (above). The approved text of this
  plan still says `git init` (Goal, the one-subprocess risk, Increments G and I); it was not
  edited, and this Result is the record of the departure. The `Proposed` decision
  `install-creates-git` and the specs were edited to match.
- `install` fetches each URL source itself after the target checks; `preview` resolves from the
  cache only. A local directory is recorded in the manifest as `local:<package>`.
- The second plan build after the answer compares digests only; the bytes written come from the
  plan the owner saw.
- A store entry that already exists is a failure after writing (exit 3), never an overwrite.
- An interrupt after the first write exits 3 (`failed: interrupted`); exit 130 is for an
  interrupt before any write.
- `tests/support.drive_pty` accepts a function as the answer, so a test can type a digest it
  could not know in advance.

**Judgment calls settled in session** (2026-10-20, "go with your recommendation"): a package
directory is recognised by `package.json` and a plain directory gets its own message; the
newest matching cache copy is used and the gate decides; each preview uses a fresh seed, so its
digest is not shown; `test_cli.py` gained usage tests.

**Sample preview** (condensed from a real run; the ASCII-escaped text is what an agent sees):

```
target: /tmp/proj
command: install
state: new-missing
summary: 1 make-target, 6 create-dir, 9 create-file, 1 git-init; 2 store writes
high risk: harness module p/h
modules:
  p/h 1.0.0 (harness)
  p/notes 1.0.0 (module)
  package p from local:p
actions:
  make-target .
  create-file .workbench/local/incomplete [scratch] - 0 bytes sha256 e3b0c4... (install marker)
  git-init .git (an empty repository on branch main, written by the workbench; git is not run)
  create-file AGENTS.md [seeded] - 551 bytes sha256 7df181...
  create-file .workbench/manifest.json [module-owned] - 1533 bytes sha256 625bff...
guarded store:
  write projects/<id>/baselines sha256 1223aa...
  write projects/<id>/seen sha256 0a0150...
git: creates an empty repository on branch main; git is not run
harness: not attached (attach is not built yet)
preview only: nothing was written
```

**Completion.** The owner accepted the three decisions (`base-ships-in-distribution`,
`install-creates-git` as revised, `harness-module-writes-nothing-committed`) and had this plan
marked `Completed` on 2026-10-20. The criteria above were checked against the tests; the
security review's unresolved items are the low and informational ones listed above, which the
owner accepted by completing the plan.

**Unresolved, for the owner.**

- Optionally record R1-F1 and R1-F2 with `ask-codex decide`, and archive the review with
  `ask-codex archive --plan docs/plans/2026-10-20-base-and-manifests.md`.
- Push: the commits from `47dc677` onward are local only.
- The skeleton `config` omits `ignorecase` and `precomposeunicode`, which git sets from the
  filesystem; the plan already refuses paths that differ only by case.
- Deferred work is listed above and unchanged; attach is the next step for `install`.
